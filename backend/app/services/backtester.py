from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

import pandas as pd

from app.services.risk_manager import calculate_position_size
from app.services.signal_generator import scan_buy_signals
from app.services.technical import calc_ema, calc_sma


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TARGET_HIT = "TARGET_HIT"
    TRAILING_STOP = "TRAILING_STOP"
    TIME_EXIT = "TIME_EXIT"
    END_OF_DATA = "END_OF_DATA"


@dataclass
class SimulatedTrade:
    symbol: str
    signal_type: str
    entry_date: date
    entry_price: float
    exit_date: date
    exit_price: float
    exit_reason: ExitReason
    shares: int
    stop_loss: float
    target_price: float
    pnl: float
    pnl_pct: float
    holding_days: int


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    risk_per_trade: float = 0.02
    max_holding_days: int = 60
    trailing_stop_pct: float | None = None
    signal_types: list[str] | None = None
    cooldown_days: int = 15
    trend_filter: bool = False
    stop_loss_atr_mult: float | None = 2.0


@dataclass
class SignalTypeStats:
    signal_type: str
    trade_count: int = 0
    win_count: int = 0
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0

    @property
    def win_rate(self) -> float:
        return self.win_count / self.trade_count if self.trade_count else 0.0

    @property
    def profit_factor(self) -> float:
        return self.gross_profit / self.gross_loss if self.gross_loss > 0 else float("inf")


@dataclass
class BacktestStats:
    total_return: float = 0.0
    total_return_pct: float = 0.0
    total_pnl: float = 0.0
    trade_count: int = 0
    win_count: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    by_signal_type: dict[str, SignalTypeStats] = field(default_factory=dict)


@dataclass
class EquityPoint:
    date: date
    equity: float


@dataclass
class BacktestResult:
    symbol: str
    config: BacktestConfig
    stats: BacktestStats
    trades: list[SimulatedTrade]
    equity_curve: list[EquityPoint]


@dataclass
class _OpenPosition:
    signal_type: str
    entry_date: date
    entry_price: float
    shares: int
    stop_loss: float
    target_price: float
    trailing_stop: float | None
    highest_since_entry: float


class Backtester:
    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run(self, df: pd.DataFrame, symbol: str) -> BacktestResult:
        if df.empty or len(df) < 120:
            return BacktestResult(
                symbol=symbol,
                config=self.config,
                stats=BacktestStats(),
                trades=[],
                equity_curve=[],
            )

        capital = self.config.initial_capital
        position: _OpenPosition | None = None
        trades: list[SimulatedTrade] = []
        equity_curve: list[EquityPoint] = []
        cooldown_until: date | None = None

        start_idx = 120

        for i in range(start_idx, len(df)):
            bar = df.iloc[i]
            bar_date = bar["date"] if isinstance(bar["date"], date) else pd.Timestamp(bar["date"]).date()

            if position is not None:
                trade = self._check_exit(position, bar, bar_date, symbol)
                if trade is not None:
                    trades.append(trade)
                    capital += trade.pnl
                    if trade.exit_reason == ExitReason.STOP_LOSS and self.config.cooldown_days > 0:
                        from datetime import timedelta
                        cooldown_until = bar_date + timedelta(days=self.config.cooldown_days)
                    position = None
                else:
                    if bar["high"] > position.highest_since_entry:
                        position.highest_since_entry = bar["high"]
                    if self.config.trailing_stop_pct and position.trailing_stop is not None:
                        new_trail = position.highest_since_entry * (1 - self.config.trailing_stop_pct)
                        if new_trail > position.trailing_stop:
                            position.trailing_stop = new_trail

            if position is None:
                if cooldown_until and bar_date < cooldown_until:
                    pass
                else:
                    cooldown_until = None
                    position = self._try_entry(df, i, symbol, capital)

            mark = bar["close"]
            unrealized = position.shares * (mark - position.entry_price) if position else 0.0
            equity_curve.append(EquityPoint(date=bar_date, equity=capital + unrealized))

        if position is not None:
            last_bar = df.iloc[-1]
            last_date = last_bar["date"] if isinstance(last_bar["date"], date) else pd.Timestamp(last_bar["date"]).date()
            holding = (last_date - position.entry_date).days
            exit_price = float(last_bar["close"])
            pnl = position.shares * (exit_price - position.entry_price)
            pnl_pct = (exit_price - position.entry_price) / position.entry_price if position.entry_price else 0.0
            trade = SimulatedTrade(
                symbol=symbol,
                signal_type=position.signal_type,
                entry_date=position.entry_date,
                entry_price=position.entry_price,
                exit_date=last_date,
                exit_price=exit_price,
                exit_reason=ExitReason.END_OF_DATA,
                shares=position.shares,
                stop_loss=position.stop_loss,
                target_price=position.target_price,
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct * 100, 2),
                holding_days=holding,
            )
            trades.append(trade)
            capital += pnl
            position = None

        stats = self._compute_stats(trades, equity_curve)
        return BacktestResult(
            symbol=symbol,
            config=self.config,
            stats=stats,
            trades=trades,
            equity_curve=equity_curve,
        )

    def _check_exit(
        self, pos: _OpenPosition, bar: pd.Series, bar_date: date, symbol: str
    ) -> SimulatedTrade | None:
        holding = (bar_date - pos.entry_date).days

        if bar["low"] <= pos.stop_loss:
            return self._close(pos, bar_date, pos.stop_loss, ExitReason.STOP_LOSS, symbol, holding)

        if pos.trailing_stop is not None and bar["low"] <= pos.trailing_stop:
            return self._close(pos, bar_date, pos.trailing_stop, ExitReason.TRAILING_STOP, symbol, holding)

        if bar["high"] >= pos.target_price:
            return self._close(pos, bar_date, pos.target_price, ExitReason.TARGET_HIT, symbol, holding)

        if holding >= self.config.max_holding_days:
            return self._close(pos, bar_date, float(bar["close"]), ExitReason.TIME_EXIT, symbol, holding)

        return None

    def _close(
        self, pos: _OpenPosition, exit_date: date, exit_price: float,
        reason: ExitReason, symbol: str, holding: int,
    ) -> SimulatedTrade:
        pnl = pos.shares * (exit_price - pos.entry_price)
        pnl_pct = (exit_price - pos.entry_price) / pos.entry_price if pos.entry_price else 0.0
        return SimulatedTrade(
            symbol=symbol,
            signal_type=pos.signal_type,
            entry_date=pos.entry_date,
            entry_price=pos.entry_price,
            exit_date=exit_date,
            exit_price=round(exit_price, 2),
            exit_reason=reason,
            shares=pos.shares,
            stop_loss=pos.stop_loss,
            target_price=pos.target_price,
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct * 100, 2),
            holding_days=holding,
        )

    def _try_entry(
        self, df: pd.DataFrame, idx: int, symbol: str, capital: float,
    ) -> _OpenPosition | None:
        window = df.iloc[: idx + 1].copy()

        if self.config.trend_filter:
            close = window["close"]
            ma60 = calc_sma(close, 60)
            if len(ma60) >= 10 and pd.notna(ma60.iloc[-1]) and pd.notna(ma60.iloc[-10]):
                if float(ma60.iloc[-1]) < float(ma60.iloc[-10]):
                    return None

        signals = scan_buy_signals(window, symbol)

        if self.config.signal_types:
            signals = [s for s in signals if s.signal_type in self.config.signal_types]

        if not signals:
            return None

        sig = signals[0]

        stop_loss = sig.stop_loss
        if self.config.stop_loss_atr_mult:
            highs = window["high"].tail(14)
            lows = window["low"].tail(14)
            closes = window["close"].tail(14)
            tr_vals = []
            for j in range(1, len(highs)):
                h = float(highs.iloc[j])
                l = float(lows.iloc[j])
                pc = float(closes.iloc[j - 1])
                tr_vals.append(max(h - l, abs(h - pc), abs(l - pc)))
            if tr_vals:
                atr = sum(tr_vals) / len(tr_vals)
                atr_stop = sig.entry_price - atr * self.config.stop_loss_atr_mult
                stop_loss = round(atr_stop, 2)

        pos_result = calculate_position_size(
            account_value=capital,
            entry_price=sig.entry_price,
            stop_loss=stop_loss,
            risk_per_trade=self.config.risk_per_trade,
        )

        if pos_result.shares <= 0 or pos_result.total_cost > capital:
            return None

        bar_date = df.iloc[idx]["date"]
        if not isinstance(bar_date, date):
            bar_date = pd.Timestamp(bar_date).date()

        trailing = None
        if self.config.trailing_stop_pct:
            trailing = sig.entry_price * (1 - self.config.trailing_stop_pct)

        return _OpenPosition(
            signal_type=sig.signal_type,
            entry_date=bar_date,
            entry_price=sig.entry_price,
            shares=pos_result.shares,
            stop_loss=stop_loss,
            target_price=sig.target_price,
            trailing_stop=trailing,
            highest_since_entry=sig.entry_price,
        )

    def _compute_stats(
        self, trades: list[SimulatedTrade], equity_curve: list[EquityPoint],
    ) -> BacktestStats:
        if not trades:
            return BacktestStats()

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        total_pnl = sum(t.pnl for t in trades)

        avg_win = gross_profit / len(wins) if wins else 0.0
        avg_loss = gross_loss / len(losses) if losses else 0.0
        avg_win_pct = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0.0
        avg_loss_pct = abs(sum(t.pnl_pct for t in losses) / len(losses)) if losses else 0.0

        max_dd, max_dd_pct = self._max_drawdown(equity_curve)
        sharpe = self._sharpe_ratio(equity_curve)

        by_type: dict[str, SignalTypeStats] = {}
        for t in trades:
            st = by_type.setdefault(t.signal_type, SignalTypeStats(signal_type=t.signal_type))
            st.trade_count += 1
            st.total_pnl += t.pnl
            if t.pnl > 0:
                st.win_count += 1
                st.gross_profit += t.pnl
            else:
                st.gross_loss += abs(t.pnl)

        for st in by_type.values():
            type_wins = [t for t in trades if t.signal_type == st.signal_type and t.pnl > 0]
            type_losses = [t for t in trades if t.signal_type == st.signal_type and t.pnl <= 0]
            st.avg_win_pct = sum(t.pnl_pct for t in type_wins) / len(type_wins) if type_wins else 0.0
            st.avg_loss_pct = abs(sum(t.pnl_pct for t in type_losses) / len(type_losses)) if type_losses else 0.0

        return BacktestStats(
            total_return=round(total_pnl, 2),
            total_return_pct=round(total_pnl / self.config.initial_capital * 100, 2),
            total_pnl=round(total_pnl, 2),
            trade_count=len(trades),
            win_count=len(wins),
            win_rate=round(len(wins) / len(trades) * 100, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            avg_win_pct=round(avg_win_pct, 2),
            avg_loss_pct=round(avg_loss_pct, 2),
            profit_factor=round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf"),
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            sharpe_ratio=round(sharpe, 2),
            by_signal_type=by_type,
        )

    @staticmethod
    def _max_drawdown(curve: list[EquityPoint]) -> tuple[float, float]:
        if not curve:
            return 0.0, 0.0
        peak = curve[0].equity
        max_dd = 0.0
        max_dd_pct = 0.0
        for pt in curve:
            if pt.equity > peak:
                peak = pt.equity
            dd = peak - pt.equity
            dd_pct = dd / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        return max_dd, max_dd_pct * 100

    @staticmethod
    def _sharpe_ratio(curve: list[EquityPoint], risk_free_annual: float = 0.04) -> float:
        if len(curve) < 2:
            return 0.0
        daily_returns = []
        for i in range(1, len(curve)):
            prev = curve[i - 1].equity
            if prev > 0:
                daily_returns.append((curve[i].equity - prev) / prev)
        if not daily_returns:
            return 0.0
        mean_r = sum(daily_returns) / len(daily_returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns))
        if std_r == 0:
            return 0.0
        daily_rf = risk_free_annual / 252
        return (mean_r - daily_rf) / std_r * math.sqrt(252)
