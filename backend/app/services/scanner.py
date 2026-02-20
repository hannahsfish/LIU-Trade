"""
LEI auto-scanner: scans stock universe, finds opportunities,
manages watchlist automatically.

Scan tiers (API budget strategy):
  Tier 1 - Watchlist + positions: refresh daily (compact=1 call each)
  Tier 2 - Full universe: rotate ~50/day (full=1 call each, covers all in ~4 days)

With 72 calls/min budget:
  - Daily watchlist refresh: ~30 stocks × 1 call = 30 calls (~0.5 min)
  - Universe rotation: ~50 stocks × 1 call = 50 calls (~1 min)
  - Leaves headroom for user-triggered queries
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Signal, Watchlist
from app.services.data_fetcher import fetch_ohlcv, get_cached_row_count, get_latest_date, is_data_stale
from app.services.rate_limiter import av_limiter
from app.services.signal_generator import scan_buy_signals
from app.services.technical import run_full_analysis, detect_ma_concentration, detect_2b, calc_sma, calc_ema, calc_slope, classify_slope
from app.services.universe import get_universe

logger = logging.getLogger(__name__)

WATCHLIST_QUALIFY_MIN_RR = 2.0
WATCHLIST_MAX_SIZE = 30
UNIVERSE_BATCH_SIZE = 50


@dataclass
class ScanResult:
    symbol: str
    qualified: bool
    signals: list = field(default_factory=list)
    reason: str = ""
    score: float = 0.0


@dataclass
class ScannerState:
    running: bool = False
    last_scan_time: datetime | None = None
    last_scan_duration: float = 0
    stocks_scanned: int = 0
    opportunities_found: int = 0
    watchlist_added: int = 0
    watchlist_removed: int = 0
    errors: int = 0
    universe_offset: int = 0
    current_symbol: str = ""


scanner_state = ScannerState()


def _score_stock(analysis: dict, signals: list) -> float:
    score = 0.0

    if signals:
        best_rr = max(s.risk_reward_ratio for s in signals)
        score += min(best_rr * 10, 40)

        for s in signals:
            if s.signal_type == "MA_CONCENTRATION_BREAKOUT":
                score += 30
            elif s.signal_type == "2B_STRUCTURE":
                score += 15
            elif s.signal_type == "MA_TURN_UP":
                score += 10

    concentration = analysis.get("ma_concentration")
    if concentration:
        if concentration.level == "full":
            score += 20
        else:
            score += 10
        if concentration.breakout_detected:
            score += 15

    two_b = analysis.get("two_b_signal")
    if two_b and two_b.is_substantive and two_b.deduction_validated:
        score += 15

    ma20_turn = analysis.get("ma20_turn")
    if ma20_turn and ma20_turn.will_turn_up and ma20_turn.confidence > 0.5:
        score += 10

    return score


def _qualifies_for_watchlist(analysis: dict, signals: list) -> tuple[bool, str]:
    if not analysis:
        return False, "无分析数据"

    slopes = analysis.get("slopes", [])
    if slopes:
        last_slope = slopes[-1]
        ma60_phase = last_slope.ma60_phase
        if ma60_phase and ma60_phase.value in ("STRONG_DOWN", "EXTREME_DOWN"):
            return False, "MA60 强势下行，趋势不对"

    bias = analysis.get("bias_ratio_120")
    if bias and bias > 50:
        return False, f"乖离率 {bias:.1f}% 过高，远离均线"

    has_signal = len(signals) > 0
    concentration = analysis.get("ma_concentration")
    two_b = analysis.get("two_b_signal")
    ma20_turn = analysis.get("ma20_turn")

    near_concentration = concentration is not None
    has_2b = two_b is not None and two_b.is_substantive
    turn_expected = ma20_turn is not None and ma20_turn.will_turn_up and ma20_turn.confidence > 0.3

    if has_signal:
        return True, "有买入信号"
    if near_concentration:
        return True, f"均线密集({concentration.level})，等待突破"
    if has_2b:
        return True, "2B结构形成，观察确认"
    if turn_expected:
        return True, f"MA20即将拐头，置信度{ma20_turn.confidence:.0%}"

    return False, "无符合条件"


async def _scan_single(symbol: str, db: AsyncSession) -> ScanResult:
    try:
        df = await fetch_ohlcv(symbol, db)
        if df.empty or len(df) < 120:
            return ScanResult(symbol=symbol, qualified=False, reason="数据不足")

        analysis = run_full_analysis(df)
        if not analysis:
            return ScanResult(symbol=symbol, qualified=False, reason="分析失败")

        signals = scan_buy_signals(df, symbol)
        qualified, reason = _qualifies_for_watchlist(analysis, signals)
        score = _score_stock(analysis, signals)

        return ScanResult(
            symbol=symbol,
            qualified=qualified,
            signals=signals,
            reason=reason,
            score=score,
        )
    except Exception as e:
        logger.error(f"Scan {symbol} failed: {e}")
        return ScanResult(symbol=symbol, qualified=False, reason=f"错误: {e}")


async def _sync_watchlist(results: list[ScanResult], db: AsyncSession):
    existing = await db.execute(select(Watchlist))
    current_watchlist = {w.symbol: w for w in existing.scalars().all()}

    qualified = [r for r in results if r.qualified]
    qualified.sort(key=lambda r: r.score, reverse=True)

    for r in qualified:
        if r.symbol not in current_watchlist and len(current_watchlist) < WATCHLIST_MAX_SIZE:
            db.add(Watchlist(
                symbol=r.symbol,
                added_at=datetime.utcnow(),
                notes=r.reason,
            ))
            current_watchlist[r.symbol] = True
            scanner_state.watchlist_added += 1
            logger.info(f"+ Watchlist: {r.symbol} ({r.reason}, score={r.score:.0f})")

    not_qualified_symbols = {r.symbol for r in results if not r.qualified}
    for symbol, watchlist_item in list(current_watchlist.items()):
        if symbol in not_qualified_symbols and isinstance(watchlist_item, Watchlist):
            await db.execute(delete(Watchlist).where(Watchlist.symbol == symbol))
            scanner_state.watchlist_removed += 1
            logger.info(f"- Watchlist: {symbol}")

    for r in qualified:
        for sig in r.signals:
            db.add(Signal(
                symbol=r.symbol,
                signal_type=sig.signal_type,
                direction="BUY",
                entry_price=sig.entry_price,
                stop_loss=sig.stop_loss,
                target_price=sig.target_price,
                risk_reward_ratio=sig.risk_reward_ratio,
                position_advice=sig.position_advice,
                reasoning=sig.reasoning,
                strength=r.score,
                created_at=datetime.utcnow(),
            ))

    await db.commit()


async def run_scan(full: bool = False):
    scanner_state.running = True
    scanner_state.stocks_scanned = 0
    scanner_state.opportunities_found = 0
    scanner_state.watchlist_added = 0
    scanner_state.watchlist_removed = 0
    scanner_state.errors = 0
    start = datetime.utcnow()

    try:
        async with async_session() as db:
            symbols_to_scan = []

            existing = await db.execute(select(Watchlist))
            watchlist_symbols = [w.symbol for w in existing.scalars().all()]
            symbols_to_scan.extend(watchlist_symbols)

            universe = get_universe()
            if full:
                remaining = [s for s in universe if s not in watchlist_symbols]
            else:
                offset = scanner_state.universe_offset
                remaining = [s for s in universe if s not in watchlist_symbols]
                batch = remaining[offset:offset + UNIVERSE_BATCH_SIZE]
                scanner_state.universe_offset = (offset + UNIVERSE_BATCH_SIZE) % max(len(remaining), 1)
                remaining = batch

            symbols_to_scan.extend(remaining)

            results = []
            for symbol in symbols_to_scan:
                scanner_state.current_symbol = symbol
                result = await _scan_single(symbol, db)
                results.append(result)
                scanner_state.stocks_scanned += 1
                if result.qualified:
                    scanner_state.opportunities_found += 1
                if "错误" in result.reason:
                    scanner_state.errors += 1

            await _sync_watchlist(results, db)

    except Exception as e:
        logger.error(f"Scanner failed: {e}")
    finally:
        scanner_state.running = False
        scanner_state.last_scan_time = datetime.utcnow()
        scanner_state.last_scan_duration = (datetime.utcnow() - start).total_seconds()
        scanner_state.current_symbol = ""
        logger.info(
            f"Scan done: {scanner_state.stocks_scanned} scanned, "
            f"{scanner_state.opportunities_found} opportunities, "
            f"+{scanner_state.watchlist_added}/-{scanner_state.watchlist_removed} watchlist, "
            f"{scanner_state.errors} errors, "
            f"{scanner_state.last_scan_duration:.1f}s"
        )


def get_scanner_status() -> dict:
    return {
        "running": scanner_state.running,
        "current_symbol": scanner_state.current_symbol,
        "last_scan_time": scanner_state.last_scan_time.isoformat() if scanner_state.last_scan_time else None,
        "last_scan_duration_seconds": round(scanner_state.last_scan_duration, 1),
        "stocks_scanned": scanner_state.stocks_scanned,
        "opportunities_found": scanner_state.opportunities_found,
        "watchlist_added": scanner_state.watchlist_added,
        "watchlist_removed": scanner_state.watchlist_removed,
        "errors": scanner_state.errors,
        "universe_offset": scanner_state.universe_offset,
        "api_budget": av_limiter.stats(),
    }
