import asyncio
import logging
import os
from dataclasses import dataclass

from futu import (
    OpenSecTradeContext,
    OrderStatus,
    OrderType,
    RET_OK,
    SecurityFirm,
    TrdEnv,
    TrdMarket,
    TrdSide,
)

logger = logging.getLogger(__name__)

FUTU_MARKET_PREFIX = {
    "US": "US",
    "HK": "HK",
    "SH": "SH",
    "SZ": "SZ",
}

FUTU_ORDER_STATUS_MAP = {
    OrderStatus.SUBMITTED: "SUBMITTED",
    OrderStatus.FILLED_ALL: "FILLED",
    OrderStatus.FILLED_PART: "PARTIAL",
    OrderStatus.CANCELLED_ALL: "CANCELLED",
    OrderStatus.CANCELLED_PART: "PARTIAL",
    OrderStatus.FAILED: "FAILED",
    OrderStatus.DISABLED: "REJECTED",
    OrderStatus.DELETED: "CANCELLED",
}


@dataclass
class PlacedOrder:
    futu_order_id: str
    symbol: str
    side: str
    price: float
    quantity: int


@dataclass
class OrderInfo:
    futu_order_id: str
    status: str
    filled_price: float
    filled_quantity: int


@dataclass
class AccountInfo:
    cash: float
    total_assets: float
    market_value: float
    buying_power: float


@dataclass
class BrokerPosition:
    symbol: str
    quantity: int
    cost_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


def _to_futu_code(symbol: str, market: str = "US") -> str:
    prefix = FUTU_MARKET_PREFIX.get(market, "US")
    if "." in symbol:
        return symbol
    return f"{prefix}.{symbol}"


def _from_futu_code(futu_code: str) -> str:
    if "." in futu_code:
        return futu_code.split(".", 1)[1]
    return futu_code


class FutuBroker:
    def __init__(self) -> None:
        self._ctx: OpenSecTradeContext | None = None
        self._host = os.getenv("FUTU_HOST", "127.0.0.1")
        self._port = int(os.getenv("FUTU_PORT", "11111"))
        self._trade_pwd = os.getenv("FUTU_TRADE_PWD", "")
        self._trd_env = (
            TrdEnv.REAL
            if os.getenv("FUTU_TRD_ENV", "SIMULATE").upper() == "REAL"
            else TrdEnv.SIMULATE
        )

    @property
    def is_connected(self) -> bool:
        return self._ctx is not None

    @property
    def trd_env_label(self) -> str:
        return "REAL" if self._trd_env == TrdEnv.REAL else "SIMULATE"

    async def connect(self) -> None:
        def _connect():
            ctx = OpenSecTradeContext(
                host=self._host,
                port=self._port,
                filter_trdmarket=TrdMarket.US,
                security_firm=SecurityFirm.FUTUSECURITIES,
            )
            return ctx

        self._ctx = await asyncio.to_thread(_connect)
        logger.info(
            "Connected to FutuOpenD at %s:%s (env=%s)",
            self._host,
            self._port,
            self.trd_env_label,
        )

    async def disconnect(self) -> None:
        if self._ctx:
            ctx = self._ctx
            self._ctx = None
            await asyncio.to_thread(ctx.close)
            logger.info("Disconnected from FutuOpenD")

    async def unlock_trade(self) -> None:
        if not self._trade_pwd:
            logger.info("No trade password configured, skipping unlock")
            return
        self._ensure_connected()

        def _unlock():
            ret, data = self._ctx.unlock_trade(self._trade_pwd)
            if ret != RET_OK:
                raise RuntimeError(f"Failed to unlock trade: {data}")

        await asyncio.to_thread(_unlock)
        logger.info("Trade unlocked")

    async def place_order(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: int,
        order_type: str = "LIMIT",
    ) -> PlacedOrder:
        self._ensure_connected()

        futu_code = _to_futu_code(symbol)
        futu_side = TrdSide.BUY if side == "BUY" else TrdSide.SELL
        futu_order_type = (
            OrderType.MARKET if order_type == "MARKET" else OrderType.NORMAL
        )

        def _place():
            ret, data = self._ctx.place_order(
                price=price,
                qty=quantity,
                code=futu_code,
                trd_side=futu_side,
                order_type=futu_order_type,
                trd_env=self._trd_env,
            )
            if ret != RET_OK:
                raise RuntimeError(f"Failed to place order: {data}")
            return str(data["order_id"].iloc[0])

        futu_order_id = await asyncio.to_thread(_place)
        logger.info(
            "Order placed: %s %s %s @ %.2f x %d → futu_order_id=%s",
            side,
            symbol,
            order_type,
            price,
            quantity,
            futu_order_id,
        )
        return PlacedOrder(
            futu_order_id=futu_order_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
        )

    async def cancel_order(self, futu_order_id: str) -> None:
        self._ensure_connected()

        def _cancel():
            ret, data = self._ctx.cancel_order(
                order_id=futu_order_id,
                trd_env=self._trd_env,
            )
            if ret != RET_OK:
                raise RuntimeError(f"Failed to cancel order: {data}")

        await asyncio.to_thread(_cancel)
        logger.info("Order cancelled: %s", futu_order_id)

    async def get_order_status(self, futu_order_id: str) -> OrderInfo:
        self._ensure_connected()

        def _query():
            ret, data = self._ctx.order_list_query(trd_env=self._trd_env)
            if ret != RET_OK:
                raise RuntimeError(f"Failed to query orders: {data}")
            row = data[data["order_id"].astype(str) == futu_order_id]
            if row.empty:
                raise ValueError(f"Order not found: {futu_order_id}")
            row = row.iloc[0]
            raw_status = row["order_status"]
            status = FUTU_ORDER_STATUS_MAP.get(raw_status, "SUBMITTED")
            return OrderInfo(
                futu_order_id=futu_order_id,
                status=status,
                filled_price=float(row.get("dealt_avg_price", 0) or 0),
                filled_quantity=int(row.get("dealt_qty", 0) or 0),
            )

        return await asyncio.to_thread(_query)

    async def get_positions(self) -> list[BrokerPosition]:
        self._ensure_connected()

        def _query():
            ret, data = self._ctx.position_list_query(trd_env=self._trd_env)
            if ret != RET_OK:
                raise RuntimeError(f"Failed to query positions: {data}")
            positions = []
            for _, row in data.iterrows():
                qty = int(row.get("qty", 0) or 0)
                if qty == 0:
                    continue
                positions.append(
                    BrokerPosition(
                        symbol=_from_futu_code(row["code"]),
                        quantity=qty,
                        cost_price=float(row.get("cost_price", 0) or 0),
                        market_value=float(row.get("market_val", 0) or 0),
                        unrealized_pnl=float(row.get("pl_val", 0) or 0),
                        unrealized_pnl_pct=float(row.get("pl_ratio", 0) or 0) * 100,
                    )
                )
            return positions

        return await asyncio.to_thread(_query)

    async def get_account_info(self) -> AccountInfo:
        self._ensure_connected()

        def _query():
            ret, data = self._ctx.accinfo_query(trd_env=self._trd_env)
            if ret != RET_OK:
                raise RuntimeError(f"Failed to query account info: {data}")
            row = data.iloc[0]
            return AccountInfo(
                cash=float(row.get("cash", 0) or 0),
                total_assets=float(row.get("total_assets", 0) or 0),
                market_value=float(row.get("market_val", 0) or 0),
                buying_power=float(row.get("power", 0) or 0),
            )

        return await asyncio.to_thread(_query)

    def _ensure_connected(self) -> None:
        if not self._ctx:
            raise RuntimeError("FutuBroker not connected. Call connect() first.")


futu_broker = FutuBroker()
