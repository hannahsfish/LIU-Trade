from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.schemas import (
    DeductionPrice,
    MAConcentration,
    MAData,
    MATurnPrediction,
    SlopeData,
    SlopePhase,
    TwoBSignal,
)


def calc_sma(prices: pd.Series, period: int) -> pd.Series:
    return prices.rolling(window=period).mean()


def calc_ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()


def get_lei_mas(df: pd.DataFrame) -> pd.DataFrame:
    result = df[["date"]].copy()
    close = df["close"]
    result["ma20"] = calc_sma(close, 20)
    result["ma60"] = calc_sma(close, 60)
    result["ema120"] = calc_ema(close, 120)
    return result


def calc_slope(ma_series: pd.Series, lookback: int = 5) -> pd.Series:
    return ma_series.diff(lookback) / lookback


def classify_slope(slope: float) -> SlopePhase:
    abs_slope = abs(slope)
    if abs_slope < 0.1:
        return SlopePhase.FLAT
    if slope > 0:
        if abs_slope < 0.5:
            return SlopePhase.GENTLE_UP
        if abs_slope < 2.0:
            return SlopePhase.STRONG_UP
        return SlopePhase.EXTREME_UP
    if abs_slope < 0.5:
        return SlopePhase.GENTLE_DOWN
    if abs_slope < 2.0:
        return SlopePhase.STRONG_DOWN
    return SlopePhase.EXTREME_DOWN


def calc_deduction_prices(prices: pd.Series, period: int) -> pd.Series:
    return prices.shift(period)


def predict_ma_turn(
    df: pd.DataFrame, period: int, future_days: int = 20
) -> MATurnPrediction:
    close = df["close"]
    dates = df["date"]

    if len(close) < period + future_days:
        return MATurnPrediction(period=period, will_turn_up=False)

    current_ma = close.iloc[-period:].mean()
    last_price = close.iloc[-1]
    last_date = dates.iloc[-1]

    deduction_prices = close.iloc[-(period) : -(period) + future_days]
    if len(deduction_prices) == 0:
        return MATurnPrediction(period=period, will_turn_up=False)

    min_deduction = deduction_prices.min()
    will_turn = last_price > min_deduction

    turn_start = None
    turn_end = None
    required_price = float(min_deduction) if not deduction_prices.empty else None

    if will_turn and len(deduction_prices) > 0:
        deduction_dates = dates.iloc[-(period) : -(period) + future_days]
        if not deduction_dates.empty:
            offset_start = len(close) - 1 - deduction_dates.index[0]
            offset_end = len(close) - 1 - deduction_dates.index[-1]
            if isinstance(last_date, date):
                turn_start = last_date + timedelta(days=max(0, offset_end))
                turn_end = last_date + timedelta(days=max(0, offset_start))

    confidence = 0.0
    if required_price and last_price > required_price:
        gap_pct = (last_price - required_price) / required_price
        confidence = min(1.0, gap_pct * 5)

    return MATurnPrediction(
        period=period,
        will_turn_up=will_turn,
        required_price=round(required_price, 2) if required_price else None,
        turn_date_start=turn_start,
        turn_date_end=turn_end,
        confidence=round(confidence, 2),
    )


def calc_bias_ratio(price: float, ema120: float) -> float:
    if ema120 == 0:
        return 0.0
    return abs(price - ema120) / ema120 * 100


def detect_2b(df: pd.DataFrame) -> TwoBSignal | None:
    if len(df) < 30:
        return None

    close = df["close"]
    dates = df["date"]
    lookback = min(60, len(df) - 1)

    recent = close.iloc[-lookback:]
    recent_dates = dates.iloc[-lookback:]

    min_idx = recent.idxmin()
    min_pos = recent.index.get_loc(min_idx)

    if min_pos < 5 or min_pos > lookback - 3:
        return None

    pre_min = recent.iloc[:min_pos]
    if pre_min.empty:
        return None

    local_lows = []
    for i in range(2, len(pre_min) - 2):
        if (
            pre_min.iloc[i] < pre_min.iloc[i - 1]
            and pre_min.iloc[i] < pre_min.iloc[i - 2]
            and pre_min.iloc[i] < pre_min.iloc[i + 1]
            and pre_min.iloc[i] < pre_min.iloc[i + 2]
        ):
            local_lows.append(i)

    if not local_lows:
        return None

    point_a_pos = local_lows[-1]
    point_a_price = float(pre_min.iloc[point_a_pos])
    point_b_price = float(recent.iloc[min_pos])

    if point_b_price >= point_a_price:
        return None

    post_b = recent.iloc[min_pos + 1 :]
    if post_b.empty:
        return None

    recovery_count = (post_b > point_a_price).sum()
    if recovery_count == 0:
        return None

    recovery_price = float(post_b[post_b > point_a_price].iloc[0])
    is_substantive = recovery_count >= 2

    deduction_prices_20 = calc_deduction_prices(close, 20)
    last_deduction = deduction_prices_20.iloc[-1] if not deduction_prices_20.empty else None
    deduction_validated = (
        last_deduction is not None
        and not pd.isna(last_deduction)
        and float(close.iloc[-1]) > float(last_deduction)
    )

    return TwoBSignal(
        point_a_date=recent_dates.iloc[point_a_pos],
        point_a_price=round(point_a_price, 2),
        point_b_date=recent_dates.iloc[min_pos],
        point_b_price=round(point_b_price, 2),
        recovery_price=round(recovery_price, 2),
        is_substantive=is_substantive,
        deduction_validated=deduction_validated,
    )


def detect_ma_concentration(
    df: pd.DataFrame, timeframe: str = "daily"
) -> MAConcentration | None:
    if len(df) < 120:
        return None

    close = df["close"]
    ma20 = calc_sma(close, 20)
    ma60 = calc_sma(close, 60)
    ema120 = calc_ema(close, 120)

    last_ma20 = ma20.iloc[-1]
    last_ma60 = ma60.iloc[-1]
    last_ema120 = ema120.iloc[-1]

    if pd.isna(last_ma20) or pd.isna(last_ma60) or pd.isna(last_ema120):
        return None

    values = [float(last_ma20), float(last_ma60), float(last_ema120)]
    spread = max(values) - min(values)
    avg = np.mean(values)
    spread_ratio = spread / avg if avg > 0 else 999

    if spread_ratio > 0.05:
        return None

    level = "full" if spread_ratio < 0.02 else "partial"

    last_close = float(close.iloc[-1])
    breakout = last_close > max(values) * 1.01

    recent_vol = df["volume"].iloc[-5:].mean()
    avg_vol = df["volume"].iloc[-60:].mean()
    volume_confirmed = recent_vol > avg_vol * 1.5 if avg_vol > 0 else False

    return MAConcentration(
        level=level,
        price_range_low=round(min(values), 2),
        price_range_high=round(max(values), 2),
        spread_ratio=round(spread_ratio, 4),
        timeframe=timeframe,
        breakout_detected=breakout,
        volume_confirmed=volume_confirmed,
    )


def run_full_analysis(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {}

    close = df["close"]
    dates = df["date"]
    last_price = float(close.iloc[-1])
    last_date = dates.iloc[-1]

    mas_df = get_lei_mas(df)
    mas = []
    for _, row in mas_df.iterrows():
        mas.append(
            MAData(
                date=row["date"],
                ma20=round(row["ma20"], 2) if pd.notna(row["ma20"]) else None,
                ma60=round(row["ma60"], 2) if pd.notna(row["ma60"]) else None,
                ema120=round(row["ema120"], 2) if pd.notna(row["ema120"]) else None,
            )
        )

    ma20 = calc_sma(close, 20)
    ma60 = calc_sma(close, 60)
    ema120 = calc_ema(close, 120)

    slope_20 = calc_slope(ma20)
    slope_60 = calc_slope(ma60)
    slope_120 = calc_slope(ema120)

    slopes = []
    for i in range(len(df)):
        s20 = float(slope_20.iloc[i]) if pd.notna(slope_20.iloc[i]) else None
        s60 = float(slope_60.iloc[i]) if pd.notna(slope_60.iloc[i]) else None
        slopes.append(
            SlopeData(
                date=dates.iloc[i],
                ma20_slope=round(s20, 4) if s20 else None,
                ma60_slope=round(s60, 4) if s60 else None,
                ema120_slope=round(float(slope_120.iloc[i]), 4)
                if pd.notna(slope_120.iloc[i])
                else None,
                ma20_phase=classify_slope(s20) if s20 else None,
                ma60_phase=classify_slope(s60) if s60 else None,
            )
        )

    deductions = []
    deduct_20 = calc_deduction_prices(close, 20)
    deduct_60 = calc_deduction_prices(close, 60)
    for i in range(len(df)):
        deductions.append(
            DeductionPrice(
                date=dates.iloc[i],
                deduction_20=round(float(deduct_20.iloc[i]), 2)
                if pd.notna(deduct_20.iloc[i])
                else None,
                deduction_60=round(float(deduct_60.iloc[i]), 2)
                if pd.notna(deduct_60.iloc[i])
                else None,
            )
        )

    ma20_turn = predict_ma_turn(df, 20) if len(df) > 40 else None
    ma60_turn = predict_ma_turn(df, 60) if len(df) > 80 else None

    last_ema120 = float(ema120.iloc[-1]) if pd.notna(ema120.iloc[-1]) else None
    bias = round(calc_bias_ratio(last_price, last_ema120), 2) if last_ema120 else None

    two_b = detect_2b(df)
    concentration = detect_ma_concentration(df)

    return {
        "symbol": "",
        "last_price": round(last_price, 2),
        "last_date": last_date,
        "mas": mas,
        "slopes": slopes,
        "deduction_prices": deductions,
        "ma20_turn": ma20_turn,
        "ma60_turn": ma60_turn,
        "bias_ratio_120": bias,
        "two_b_signal": two_b,
        "ma_concentration": concentration,
    }
