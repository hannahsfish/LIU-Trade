from dataclasses import dataclass


@dataclass
class PositionSizeResult:
    shares: int
    risk_amount: float
    total_cost: float


def calculate_position_size(
    account_value: float,
    entry_price: float,
    stop_loss: float,
    risk_per_trade: float = 0.02,
) -> PositionSizeResult:
    risk_amount = account_value * risk_per_trade
    risk_per_share = abs(entry_price - stop_loss)

    if risk_per_share <= 0:
        return PositionSizeResult(shares=0, risk_amount=0, total_cost=0)

    shares = int(risk_amount / risk_per_share)
    total_cost = shares * entry_price

    return PositionSizeResult(
        shares=shares,
        risk_amount=round(risk_amount, 2),
        total_cost=round(total_cost, 2),
    )


def validate_plan(
    entry_price: float,
    stop_loss: float,
    target_price: float,
    risk_reward_ratio: float,
    max_loss_pct: float,
) -> list[str]:
    errors = []

    if risk_reward_ratio < 2.0:
        errors.append(f"盈亏比 {risk_reward_ratio} < 2.0，风险过高")

    if max_loss_pct >= 10.0:
        errors.append(f"最大亏损 {max_loss_pct}% >= 10%，止损幅度过大")

    if stop_loss >= entry_price:
        errors.append("止损价 >= 入场价，逻辑错误")

    if target_price <= entry_price:
        errors.append("目标价 <= 入场价，无利润空间")

    return errors
