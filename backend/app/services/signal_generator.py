import pandas as pd

from app.schemas import BuySignalResponse
from app.services.technical import (
    calc_bias_ratio,
    calc_ema,
    calc_sma,
    detect_2b,
    detect_ma_concentration,
    predict_ma_turn,
)


def scan_buy_signals(df: pd.DataFrame, symbol: str) -> list[BuySignalResponse]:
    if df.empty or len(df) < 120:
        return []

    signals = []
    close = df["close"]
    last_price = float(close.iloc[-1])

    ma20 = calc_sma(close, 20)
    ma60 = calc_sma(close, 60)
    ema120 = calc_ema(close, 120)

    last_ma60 = float(ma60.iloc[-1]) if pd.notna(ma60.iloc[-1]) else None
    last_ema120 = float(ema120.iloc[-1]) if pd.notna(ema120.iloc[-1]) else None

    two_b = detect_2b(df)
    if two_b and two_b.is_substantive:
        stop_loss = round(two_b.point_b_price * 0.98, 2)
        target = round(last_ma60, 2) if last_ma60 else round(last_price * 1.15, 2)
        risk = last_price - stop_loss
        reward = target - last_price
        rr = round(reward / risk, 2) if risk > 0 else 0

        if rr >= 2.0 and risk / last_price < 0.10:
            signals.append(
                BuySignalResponse(
                    signal_type="2B_STRUCTURE",
                    position_advice="PROBE",
                    entry_price=round(last_price, 2),
                    stop_loss=stop_loss,
                    target_price=target,
                    risk_reward_ratio=rr,
                    reasoning=f"2B结构形成: 前低{two_b.point_a_price} → 新低{two_b.point_b_price} → 收回{two_b.recovery_price}。"
                    f"{'抵扣价验证通过' if two_b.deduction_validated else '等待抵扣价验证'}。轻仓试探。",
                )
            )

    concentration = detect_ma_concentration(df)
    if concentration and concentration.breakout_detected and concentration.volume_confirmed:
        stop_loss = round(concentration.price_range_low * 0.98, 2)
        target = round(last_price * 1.20, 2)
        risk = last_price - stop_loss
        reward = target - last_price
        rr = round(reward / risk, 2) if risk > 0 else 0

        if rr >= 2.0:
            signals.append(
                BuySignalResponse(
                    signal_type="MA_CONCENTRATION_BREAKOUT",
                    position_advice="CONFIRM",
                    entry_price=round(last_price, 2),
                    stop_loss=stop_loss,
                    target_price=target,
                    risk_reward_ratio=rr,
                    reasoning=f"均线密集({concentration.level})突破: 密集区{concentration.price_range_low}-{concentration.price_range_high}，"
                    f"放量突破确认。重仓机会。",
                )
            )

    ma20_turn = predict_ma_turn(df, 20)
    if ma20_turn.will_turn_up and ma20_turn.confidence > 0.5:
        stop_loss = round(last_price * 0.95, 2)
        target = round(last_ma60, 2) if last_ma60 and last_ma60 > last_price else round(last_price * 1.12, 2)
        risk = last_price - stop_loss
        reward = target - last_price
        rr = round(reward / risk, 2) if risk > 0 else 0

        if rr >= 2.0:
            signals.append(
                BuySignalResponse(
                    signal_type="MA_TURN_UP",
                    position_advice="PROBE",
                    entry_price=round(last_price, 2),
                    stop_loss=stop_loss,
                    target_price=target,
                    risk_reward_ratio=rr,
                    reasoning=f"MA20即将拐头向上: 抵扣价{ma20_turn.required_price}，"
                    f"当前价{round(last_price, 2)}高于抵扣价，置信度{ma20_turn.confidence}。",
                )
            )

    return signals
