# LEI 交易系统 - 软件架构设计 v2

## 技术栈
- **后端**: Python 3.12+ / FastAPI
- **前端**: React 19 + TypeScript + Tailwind CSS 4
- **数据可视化**: Lightweight Charts (TradingView) + 自定义 Volume Profile 组件
- **数据存储**: SQLite (开发) / PostgreSQL (生产)
- **任务调度**: APScheduler (后台扫描 + 提醒)
- **实时通信**: WebSocket (FastAPI WebSocket + 浏览器通知)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (React)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ 指令面板  │ │ 持仓总览 │ │ 机会雷达 │ │ 交易记录/复盘     │  │
│  │ (首页)   │ │          │ │          │ │                   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬───────────┘  │
└───────┼────────────┼────────────┼────────────────┼──────────────┘
        │            │            │                │
        └────────────┴─────┬──────┴────────────────┘
                           │ HTTP + WebSocket
┌──────────────────────────┼────────────────────────────────────────┐
│                     后端 (FastAPI)                                  │
│                                                                    │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │                     API Layer                              │    │
│  │  /stocks/*  /analysis/*  /signals/*  /plans/*  /alerts/*  │    │
│  └─────────────────────────┬─────────────────────────────────┘    │
│                            │                                       │
│  ┌─────────────────────────┼─────────────────────────────────┐    │
│  │                   Service Layer                            │    │
│  │                                                            │    │
│  │  ┌────────────┐ ┌──────────────┐ ┌──────────────────┐    │    │
│  │  │ DataFetcher│ │ Fundamental  │ │ Technical        │    │    │
│  │  │            │ │ Analyzer     │ │ Analyzer         │    │    │
│  │  └────────────┘ └──────────────┘ │ - MA/EMA         │    │    │
│  │                                   │ - 抵扣价推演      │    │    │
│  │  ┌────────────┐ ┌──────────────┐ │ - 协率计算        │    │    │
│  │  │ Signal     │ │ Risk         │ │ - 2B结构+验证     │    │    │
│  │  │ Generator  │ │ Manager      │ │ - 均线密集        │    │    │
│  │  │ - 买入信号  │ │ - 仓位计算   │ │ - 筹码峰         │    │    │
│  │  │ - 卖出信号  │ │ - 止损管理   │ │ - 乖离率         │    │    │
│  │  │ - 趋势预警  │ │ - 盈亏比     │ └──────────────────┘    │    │
│  │  └────────────┘ └──────────────┘                          │    │
│  │                                                            │    │
│  │  ┌────────────────────┐ ┌─────────────────────────────┐   │    │
│  │  │ TradePlanManager   │ │ AlertEngine                 │   │    │
│  │  │ - 三有计划制定      │ │ - 定时扫描                   │   │    │
│  │  │ - 计划跟踪         │ │ - 趋势变化检测               │   │    │
│  │  │ - 执行记录         │ │ - WebSocket推送              │   │    │
│  │  └────────────────────┘ │ - 浏览器通知                 │   │    │
│  │                         └─────────────────────────────┘   │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │                     Data Layer                             │    │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────────────┐        │    │
│  │  │ yfinance │  │ FMP API  │  │ SQLite/PostgreSQL │        │    │
│  │  └─────────┘  └──────────┘  └───────────────────┘        │    │
│  └───────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 核心模块设计

### 1. 数据获取模块 (DataFetcher)

```python
class DataFetcher:
    get_ohlcv(symbol, start, end, interval="1d") -> DataFrame
    get_weekly_ohlcv(symbol, start, end) -> DataFrame
    get_financials(symbol) -> FinancialData
    search_stocks(query) -> List[StockInfo]
    get_stock_info(symbol) -> StockInfo
```

数据源:
- 价格数据 (OHLCV): yfinance — 日线 + 周线
- 财务数据: Financial Modeling Prep API

### 2. 基本面分析模块 (FundamentalAnalyzer)

```python
class FundamentalAnalyzer:
    screen_stocks(criteria: ScreenCriteria) -> List[ScreenResult]
    check_financial_health(symbol) -> HealthReport
    calculate_valuation(symbol) -> ValuationReport
```

筛选标准 (LEI框架硬性指标):
- 年收入 > $100M
- 收入增长 15-20%（10%以下排除，40%以上警惕）
- 运营现金流 > 0
- 自由现金流 > 0
- 运营利润率：同行业比较
- 避雷针：结构性亏损（利润为负、债务>收入）直接排除

### 3. 技术分析模块 (TechnicalAnalyzer)

LEI 框架的核心计算引擎。

```python
class TechnicalAnalyzer:

    # === 均线体系 (固定周期: 20/60/120) ===
    calculate_ma(prices, period) -> Series           # SMA
    calculate_ema(prices, period) -> Series          # EMA
    get_lei_mas(prices) -> LeiMAs                    # 返回 MA20, MA60, EMA120 全套

    # === 协率 (Slope) ===
    calculate_slope(ma_series, lookback=5) -> Series
    classify_slope_phase(slope_series) -> SlopePhase
    # SlopePhase: FLAT / GENTLE_UP / STRONG_UP / EXTREME_UP / GENTLE_DOWN / STRONG_DOWN / EXTREME_DOWN

    # === 抵扣价推演 (画框法) ===
    calculate_deduction_prices(prices, period) -> Series
    predict_ma_turn(prices, period, future_days=20) -> MATurnPrediction
    # MATurnPrediction:
    #   will_turn_up: bool
    #   required_price: float        # 必由之路价格
    #   turn_date_range: (date, date) # 画框时间范围
    #   deduction_prices: Series      # 未来N天抵扣价序列
    #   confidence: float

    # === 2B结构检测 (含抵扣价验证) ===
    detect_2b_structure(prices, volumes) -> Optional[TwoBSignal]
    # TwoBSignal:
    #   point_a: (date, price)       # 前低点
    #   point_b: (date, price)       # 新低点
    #   recovery_price: float        # 站回价格
    #   is_substantive: bool         # 实质性收回（非下影线）
    #   deduction_validated: bool    # 抵扣价窗口验证通过
    #   ma20_turn_window: (date, date) # MA20拐头时间窗口

    # === 均线密集检测 ===
    detect_ma_concentration(prices, timeframe="daily") -> Optional[MAConcentration]
    # MAConcentration:
    #   level: "full" | "partial"    # 三线合一 vs 20+60汇聚
    #   price_range: (float, float)  # 密集区间
    #   spread_ratio: float          # 极差/均值比
    #   timeframe: "daily" | "weekly"
    #   breakout_detected: bool      # 是否已突破发散
    #   volume_confirmed: bool       # 放量确认

    # === 筹码峰 (Volume Profile) ===
    calculate_volume_profile(prices, volumes, time_range: TimeRange) -> VolumeProfile
    find_chip_peaks(volume_profile) -> List[ChipPeak]
    suggest_volume_profile_range(prices, mode="support"|"trend") -> TimeRange
    # mode="support": 自动选取前期震荡区间
    # mode="trend": 自动选取底部启动到现在

    # === 乖离率 ===
    calculate_bias_ratio(price, ema120) -> float
    # 公式: |price - ema120| / ema120 * 100%
    detect_bias_extreme(bias) -> Optional[BiasExtreme]
    # 50%+ = WARNING, 70%+ = EXTREME
```

### 4. 信号生成模块 (SignalGenerator)

```python
class SignalGenerator:

    # === 趋势判断 ===
    determine_clock_direction(analysis: FullAnalysis) -> ClockDirection
    # ClockDirection: 1_OCLOCK / 2_OCLOCK / 3_OCLOCK / 4_OCLOCK / 5_OCLOCK

    # === 买入信号 ===
    scan_buy_signals(symbol) -> List[BuySignal]
    # BuySignal:
    #   type: "2B_STRUCTURE" | "MA_CONCENTRATION_BREAKOUT" | "PULLBACK_TO_CHIP_PEAK" | "MA_TURN_UP"
    #   position_advice: "PROBE" | "CONFIRM"   # 轻仓试探 vs 重仓确认
    #   entry_price: float
    #   stop_loss: float
    #   stop_loss_type: "PREV_LOW" | "CHIP_PEAK_BOTTOM" | "LOGIC_INVALIDATION"
    #   target_price: float                     # 上方均线密集区
    #   risk_reward_ratio: float                # 必须 >= 2.0
    #   max_loss_pct: float                     # 必须 < 10%
    #   reasoning: str                          # 交易逻辑说明

    # === 卖出信号 ===
    scan_sell_signals(symbol, position: Position) -> List[SellSignal]
    # SellSignal:
    #   type: "TARGET_REACHED" | "BIAS_EXTREME" | "SLOPE_EXTREME" | "DEDUCTION_REVERSAL" | "STOP_LOSS_HIT" | "LOGIC_INVALIDATED"
    #   urgency: "IMMEDIATE" | "WATCH" | "PLAN"
    #   reasoning: str

    # === 趋势变化预警（持仓期间） ===
    scan_trend_changes(positions: List[Position]) -> List[TrendAlert]
    # TrendAlert:
    #   symbol: str
    #   alert_type: "SLOPE_WEAKENING" | "DEDUCTION_TURNING_DOWN" | "BIAS_APPROACHING_EXTREME" | "SUPPORT_BREAKING" | "STOP_LOSS_APPROACHING"
    #   severity: "INFO" | "WARNING" | "CRITICAL"
    #   suggested_action: str                   # 具体操作建议
    #   current_price: float
    #   key_level: float                        # 关键价位
```

### 5. 交易计划模块 (TradePlanManager) — 新增

实现 LEI "三有"原则的核心模块。

```python
class TradePlanManager:

    create_plan(symbol, signal: BuySignal) -> TradePlan
    # TradePlan:
    #   symbol: str
    #   # 有预期
    #   expectation: str              # 预期走势描述（如"MA60即将拐头"）
    #   clock_direction: ClockDirection
    #   target_price: float           # 目标价（上方密集区）
    #   # 有底线
    #   stop_loss: float
    #   stop_loss_type: str
    #   max_loss_pct: float
    #   # 有计划
    #   entry_price: float
    #   position_type: "PROBE" | "CONFIRM"
    #   position_size: int            # 建议股数
    #   risk_reward_ratio: float
    #   # 状态
    #   status: "DRAFT" | "ACTIVE" | "EXECUTED" | "STOPPED_OUT" | "TARGET_HIT" | "CANCELLED"

    execute_plan(plan_id, actual_entry_price, actual_quantity) -> Position
    close_position(position_id, exit_price, reason) -> TradeResult
    get_active_plans() -> List[TradePlan]
    get_trade_history() -> List[TradeResult]
```

### 6. 风险管理模块 (RiskManager)

```python
class RiskManager:

    calculate_position_size(
        account_value: float,
        entry_price: float,
        stop_loss: float,
        risk_per_trade: float = 0.02  # 单笔风险不超过总资金2%
    ) -> PositionSize

    validate_plan(plan: TradePlan) -> ValidationResult
    # 验证:
    #   - 盈亏比 >= 2:1
    #   - 止损幅度 < 10%
    #   - 趋势方向为2点钟
    #   - 不与现有持仓冲突

    get_portfolio_risk() -> PortfolioRisk
    # 总仓位、行业集中度、最大回撤
```

### 7. 提醒引擎 (AlertEngine) — 新增

```python
class AlertEngine:

    # 后台定时任务（APScheduler）
    scan_watchlist()      # 扫描关注列表，检测新买入机会
    scan_positions()      # 扫描持仓，检测趋势变化和止损触发
    scan_plans()          # 扫描交易计划，检测入场条件是否到达

    # 提醒方式
    push_websocket(alert: Alert)       # 实时推送到前端
    push_browser_notification(alert)   # 浏览器原生通知
    store_alert(alert)                 # 存储到数据库供查看
```

---

## API 设计

### 股票接口
```
GET  /api/stocks/search?q={query}
GET  /api/stocks/{symbol}
GET  /api/stocks/{symbol}/ohlcv?interval=daily|weekly&start=&end=
GET  /api/stocks/{symbol}/financials
```

### 分析接口
```
GET  /api/analysis/{symbol}/fundamental
GET  /api/analysis/{symbol}/technical
GET  /api/analysis/{symbol}/full
GET  /api/analysis/{symbol}/deduction?period=20|60     # 抵扣价推演
GET  /api/analysis/{symbol}/volume-profile?mode=support|trend  # 筹码峰
POST /api/analysis/screen                               # 基本面筛选
```

### 信号接口
```
GET  /api/signals/{symbol}/buy
GET  /api/signals/{symbol}/sell
GET  /api/signals/opportunities                         # 全市场扫描
GET  /api/signals/watchlist                             # 关注列表信号
```

### 交易计划接口
```
GET    /api/plans                                       # 所有计划
POST   /api/plans                                       # 创建计划
GET    /api/plans/{id}
PUT    /api/plans/{id}                                  # 更新计划
POST   /api/plans/{id}/execute                          # 执行计划（记录买入）
POST   /api/plans/{id}/close                            # 平仓
DELETE /api/plans/{id}                                  # 取消计划
```

### 持仓接口
```
GET  /api/positions                                     # 当前持仓
GET  /api/positions/{id}
POST /api/positions/{id}/adjust-stop                    # 调整止损
GET  /api/positions/history                             # 历史交易
GET  /api/positions/performance                         # 绩效统计
```

### 指令接口 (前端首页核心)
```
GET  /api/commands                                      # 获取当前所有指令（红/黄/绿）
POST /api/commands/{id}/execute                         # 用户反馈已执行（含实际价格/数量）
POST /api/commands/{id}/dismiss                         # 用户忽略该指令
```

### 提醒接口
```
GET  /api/alerts                                        # 提醒列表
PUT  /api/alerts/{id}/read                              # 标记已读
WS   /ws/alerts                                         # WebSocket实时推送
```

---

## 数据库设计

```sql
-- 股票基本信息
stocks (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    industry TEXT,
    market_cap BIGINT,
    last_updated TIMESTAMP
)

-- 价格历史 (日线)
price_history (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, date)
)

-- 价格历史 (周线)
price_history_weekly (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    week_start DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, week_start)
)

-- 财务数据
financials (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    period DATE NOT NULL,
    revenue BIGINT,
    revenue_growth REAL,
    operating_income BIGINT,
    operating_cf BIGINT,
    free_cf BIGINT,
    ebit_margin REAL,
    debt_to_revenue REAL,
    UNIQUE(symbol, period)
)

-- 关注列表
watchlist (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
)

-- 交易计划 (三有原则)
trade_plans (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 有预期
    expectation TEXT NOT NULL,
    clock_direction TEXT NOT NULL,
    target_price REAL NOT NULL,
    -- 有底线
    stop_loss REAL NOT NULL,
    stop_loss_type TEXT NOT NULL,
    max_loss_pct REAL NOT NULL,
    -- 有计划
    entry_price REAL NOT NULL,
    position_type TEXT NOT NULL,       -- PROBE / CONFIRM
    position_size INTEGER,
    risk_reward_ratio REAL NOT NULL,
    -- 状态
    status TEXT DEFAULT 'DRAFT',
    -- 关联信号
    signal_type TEXT,
    signal_reasoning TEXT
)

-- 持仓
positions (
    id INTEGER PRIMARY KEY,
    plan_id INTEGER REFERENCES trade_plans(id),
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    entry_date DATE NOT NULL,
    stop_loss REAL NOT NULL,
    target_price REAL NOT NULL,
    -- 平仓
    exit_price REAL,
    exit_date DATE,
    exit_reason TEXT,
    -- 盈亏
    pnl REAL,
    pnl_pct REAL,
    status TEXT DEFAULT 'OPEN'
)

-- 提醒记录
alerts (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,            -- INFO / WARNING / CRITICAL
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    suggested_action TEXT,
    current_price REAL,
    key_level REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    status TEXT DEFAULT 'UNREAD'
)

-- 操作指令 (前端首页核心)
commands (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    priority TEXT NOT NULL,            -- RED / YELLOW / GREEN
    action TEXT NOT NULL,              -- BUY / SELL / HOLD / WATCH / STOP_LOSS
    headline TEXT NOT NULL,            -- 一句话指令: "立即止损 TSLA | 卖出 50股"
    detail TEXT,                       -- 展开后的简要理由
    suggested_price REAL,
    suggested_quantity INTEGER,
    stop_loss REAL,
    target_price REAL,
    risk_reward_ratio REAL,
    -- 关联
    plan_id INTEGER REFERENCES trade_plans(id),
    position_id INTEGER REFERENCES positions(id),
    signal_id INTEGER REFERENCES signals(id),
    -- 执行反馈
    status TEXT DEFAULT 'PENDING',     -- PENDING / EXECUTED / DISMISSED / EXPIRED
    actual_price REAL,
    actual_quantity INTEGER,
    executed_at TIMESTAMP,
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
)

-- 信号记录
signals (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    direction TEXT NOT NULL,           -- BUY / SELL
    entry_price REAL,
    stop_loss REAL,
    target_price REAL,
    risk_reward_ratio REAL,
    position_advice TEXT,              -- PROBE / CONFIRM
    reasoning TEXT,
    strength REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
)
```

---

## 前端设计哲学

**核心范式转变：软件是指挥官，用户是执行人。**

用户不需要看懂图表、不需要自己分析。软件负责：
1. 告诉用户"现在做什么"（具体到股票代码、价格、数量）
2. 告诉用户"什么时候做"（到价提醒）
3. 用户执行后反馈结果，软件负责盯盘和复盘

**设计原则：**
- 零分析负担：用户不需要理解任何技术指标
- 一句话指令：每个操作用一句话说清楚
- 红绿灯系统：绿=执行，黄=关注，红=立即行动

---

## 前端页面设计

### 页面1: 指令面板 (首页，唯一常驻页面)

打开就是一个**待办列表**，按优先级排序。每条指令格式统一：

```
[红] 立即止损 TSLA | 卖出 50股 | 当前 $241 已跌破止损线 $245
    → 点击"已执行" 输入实际卖出价

[红] 入场机会到达 NVDA | 买入 30股 @ $875附近 | 止损 $820 | 目标 $1050
    → 点击"已买入" 输入实际买入价和数量

[黄] 关注 GOOGL | MA60 即将拐头（3天内）| 等待确认信号
    → 无需操作，持续跟踪中

[绿] 持仓正常 AAPL | 盈利 +12.3% | 距目标还有 18% 空间
    → 继续持有，无需操作
```

**页面结构：**
- 顶部：账户总览（总资金 / 持仓市值 / 今日盈亏 / 可用资金）
- 主体：指令列表（按颜色分区：红→黄→绿）
  - 红色区：需要立即执行的操作（止损/入场/平仓）
  - 黄色区：需要关注但暂不操作的变化
  - 绿色区：一切正常的持仓状态
- 每条指令可展开查看简要理由（一段话解释为什么）
- 执行反馈：点击后弹出简单表单（实际价格、数量）

### 页面2: 持仓总览

当前所有持仓的状态：

```
AAPL  100股  成本$189  现价$211  盈亏+11.6%  状态:正常持有
  止损: $178  目标: $245  盈亏比 1:2.5
  下一关注点: EMA120乖离率接近40%，注意减速信号

MSFT  50股   成本$415  现价$408  盈亏-1.7%   状态:观察中
  止损: $395  目标: $480  盈亏比 1:3.2
  下一关注点: 抵扣价窗口3天后打开，预计MA20拐头
```

- 每个持仓一张卡片
- 点击可看完整 K线图（预配置好所有LEI指标）
- "录入操作"按钮：卖出/加仓/调整止损

### 页面3: 机会雷达

系统自动扫描发现的买入机会：

```
[强] NVDA — 均线密集突破 (重仓机会)
  建议: 买入 @ $875 | 止损 $820 | 目标 $1050 | 盈亏比 3.2:1
  理由: 周线20/60/120均线密集后放量突破，2点钟方向确认
  → "创建交易计划"

[弱] AMZN — 2B结构形成 (试探机会)
  建议: 轻仓试探 @ $186 | 止损 $178 | 目标 $210 | 盈亏比 3:1
  理由: 日线2B结构+抵扣价窗口验证通过，但MA60未拐头
  → "创建交易计划"
```

- 按信号强度排序（强=重仓机会，弱=试探机会）
- 一键创建交易计划（所有参数自动填充）
- 点击可看图表（了解为什么推荐）

### 页面4: 交易记录 (复盘)

所有已结束交易的成绩单：

```
总览: 胜率 62% | 平均盈亏比 2.8:1 | 本月收益 +8.3%

最近交易:
✅ GOOGL  +18.2%  持有23天  (均线密集突破 → 目标到达)
❌ META   -6.1%   持有5天   (2B结构 → 逻辑证伪止损)
✅ AAPL   +9.7%   持有31天  (回撤至筹码峰 → 目标到达)
```

- 每笔交易可展开看完整复盘（买入理由、卖出理由、图表回顾）
- 统计面板：胜率、盈亏比、月度收益曲线

### 图表页 (辅助，非主要页面)

用户从指令/持仓/机会点击"查看图表"时打开：
- K线 + MA20/MA60/EMA120
- 抵扣价推演画框
- Volume Profile (筹码峰)
- 2B结构/均线密集标记
- 买卖点标注

这是辅助验证页面，用户不需要主动分析，只是"看一眼确认"。

---

## 后台任务

| 任务 | 频率 | 内容 |
|------|------|------|
| 价格数据更新 | 每日收盘后 | 更新所有关注股票的日线/周线数据 |
| 持仓趋势扫描 | 每日收盘后 | 检测持仓股票的趋势变化、止损触发 |
| 关注列表机会扫描 | 每日收盘后 | 扫描关注列表的买入信号 |
| 交易计划检查 | 每日收盘后 | 检测等待中的计划是否到达入场条件 |

---

## 部署架构

```
开发环境:
  - 后端: FastAPI (localhost:8000) + WebSocket
  - 前端: Vite dev server (localhost:5173)
  - 数据库: SQLite

生产环境:
  - 后端: Docker + Uvicorn
  - 前端: Nginx (静态文件)
  - 数据库: PostgreSQL
  - 定时任务: APScheduler (进程内)
```

---

## 开发计划

### MVP
1. 项目框架搭建 (后端 + 前端)
2. 数据获取 (yfinance 日线/周线)
3. 核心技术指标 (MA20/MA60/EMA120 + 抵扣价 + 协率)
4. K线图表 (均线 + 成交量 + 抵扣价线)
5. 2B结构检测 + 均线密集检测
6. 买入信号生成
7. 交易计划创建/跟踪

### V1.0
1. 筹码峰 (Volume Profile) 计算 + 可视化
2. 完整卖出信号体系
3. 基本面筛选
4. 提醒系统 (WebSocket + 浏览器通知)
5. 持仓管理 + 绩效统计
6. 响应式UI

---

## 最后更新
2026-02-19 - v2: 对照 LEI 完整框架重写，修复 7 项架构缺陷
