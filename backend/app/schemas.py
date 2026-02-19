from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class Priority(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WATCH = "WATCH"
    STOP_LOSS = "STOP_LOSS"


class CommandStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    DISMISSED = "DISMISSED"
    EXPIRED = "EXPIRED"


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXECUTED = "EXECUTED"
    STOPPED_OUT = "STOPPED_OUT"
    TARGET_HIT = "TARGET_HIT"
    CANCELLED = "CANCELLED"


class PositionType(str, Enum):
    PROBE = "PROBE"
    CONFIRM = "CONFIRM"


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class SignalType(str, Enum):
    TWO_B_STRUCTURE = "2B_STRUCTURE"
    MA_CONCENTRATION_BREAKOUT = "MA_CONCENTRATION_BREAKOUT"
    MA_TURN_UP = "MA_TURN_UP"


class SlopePhase(str, Enum):
    FLAT = "FLAT"
    GENTLE_UP = "GENTLE_UP"
    STRONG_UP = "STRONG_UP"
    EXTREME_UP = "EXTREME_UP"
    GENTLE_DOWN = "GENTLE_DOWN"
    STRONG_DOWN = "STRONG_DOWN"
    EXTREME_DOWN = "EXTREME_DOWN"


# --- Request schemas ---


class StockSearchResult(BaseModel):
    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: int | None = None


class OHLCVBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVResponse(BaseModel):
    symbol: str
    interval: str
    bars: list[OHLCVBar]


class MAData(BaseModel):
    date: date
    ma20: float | None = None
    ma60: float | None = None
    ema120: float | None = None


class SlopeData(BaseModel):
    date: date
    ma20_slope: float | None = None
    ma60_slope: float | None = None
    ema120_slope: float | None = None
    ma20_phase: SlopePhase | None = None
    ma60_phase: SlopePhase | None = None


class DeductionPrice(BaseModel):
    date: date
    deduction_20: float | None = None
    deduction_60: float | None = None


class MATurnPrediction(BaseModel):
    period: int
    will_turn_up: bool
    required_price: float | None = None
    turn_date_start: date | None = None
    turn_date_end: date | None = None
    confidence: float = 0.0


class TwoBSignal(BaseModel):
    point_a_date: date
    point_a_price: float
    point_b_date: date
    point_b_price: float
    recovery_price: float
    is_substantive: bool
    deduction_validated: bool


class MAConcentration(BaseModel):
    level: str
    price_range_low: float
    price_range_high: float
    spread_ratio: float
    timeframe: str
    breakout_detected: bool
    volume_confirmed: bool


class TechnicalAnalysis(BaseModel):
    symbol: str
    last_price: float
    last_date: date
    mas: list[MAData]
    slopes: list[SlopeData]
    deduction_prices: list[DeductionPrice]
    ma20_turn: MATurnPrediction | None = None
    ma60_turn: MATurnPrediction | None = None
    bias_ratio_120: float | None = None
    two_b_signal: TwoBSignal | None = None
    ma_concentration: MAConcentration | None = None


class BuySignalResponse(BaseModel):
    signal_type: str
    position_advice: str
    entry_price: float
    stop_loss: float
    target_price: float
    risk_reward_ratio: float
    reasoning: str


class CommandResponse(BaseModel):
    id: int
    symbol: str
    priority: str
    action: str
    headline: str
    detail: str | None = None
    suggested_price: float | None = None
    suggested_quantity: int | None = None
    stop_loss: float | None = None
    target_price: float | None = None
    risk_reward_ratio: float | None = None
    status: str
    created_at: datetime


class ExecuteCommandRequest(BaseModel):
    actual_price: float
    actual_quantity: int


class CreatePlanRequest(BaseModel):
    symbol: str
    expectation: str
    clock_direction: str
    target_price: float
    stop_loss: float
    stop_loss_type: str
    max_loss_pct: float
    entry_price: float
    position_type: PositionType
    position_size: int | None = None
    risk_reward_ratio: float
    signal_type: str | None = None
    signal_reasoning: str | None = None


class PlanResponse(BaseModel):
    id: int
    symbol: str
    expectation: str
    clock_direction: str
    target_price: float
    stop_loss: float
    stop_loss_type: str
    max_loss_pct: float
    entry_price: float
    position_type: str
    position_size: int | None = None
    risk_reward_ratio: float
    status: str
    signal_type: str | None = None
    signal_reasoning: str | None = None
    created_at: datetime


class ExecutePlanRequest(BaseModel):
    actual_price: float
    actual_quantity: int


class PositionResponse(BaseModel):
    id: int
    plan_id: int | None = None
    symbol: str
    quantity: int
    entry_price: float
    entry_date: date
    stop_loss: float
    target_price: float
    current_price: float | None = None
    pnl: float | None = None
    pnl_pct: float | None = None
    status: str


class ClosePositionRequest(BaseModel):
    exit_price: float
    exit_reason: str
