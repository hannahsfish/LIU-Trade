# LEI 交易系统 - 软件架构设计

## 技术栈
- **后端**: Python + FastAPI
- **前端**: React + TypeScript + Tailwind CSS
- **数据可视化**: Lightweight Charts (TradingView)
- **数据存储**: SQLite (本地) + 可选 PostgreSQL
- **任务调度**: APScheduler

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React)                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │
│  │ 股票搜索 │  │ K线图表 │  │ 信号面板 │  │ 模拟交易    │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └──────┬──────┘ │
└───────┼────────────┼────────────┼───────────────┼─────────┘
        │            │            │               │
        └────────────┴─────┬──────┴───────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────┼──────────────────────────────────┐
│                    后端 (FastAPI)                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    API Router                         │  │
│  │  /stocks/*  /analysis/*  /signals/*  /trading/*      │  │
│  └─────────────────────────┬────────────────────────────┘  │
│                            │                                │
│  ┌────────────┬────────────┼────────────┬───────────────┐  │
│  │ 数据获取   │ 基本面分析  │ 技术分析    │ 信号生成      │  │
│  │ Service   │ Service    │ Service    │ Service       │  │
│  └─────┬─────┴──────┬─────┴─────┬─────┴───────┬───────┘  │
│        │             │           │             │           │
│  ┌─────┴─────────────┴───────────┴─────────────┴────────┐  │
│  │                   Data Layer                        │  │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────────────┐  │  │
│  │  │ yfinance │  │ FMP API  │  │ SQLite/PostgreSQL │  │  │
│  │  └─────────┘  └──────────┘  └───────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心模块设计

### 1. 数据获取模块 (DataFetcher)

```python
class DataFetcher:
    - get_stock_price(symbol: str, period: str) -> pd.DataFrame
    - get_stock_ohlcv(symbol: str, start: date, end: date) -> pd.DataFrame
    - get_intraday_data(symbol: str, interval: str) -> pd.DataFrame
    - get_financials(symbol: str) -> FinancialData
    - get_fundamentals(symbol: str) -> FundamentalData
```

**数据源**:
- 价格数据: yfinance (Yahoo Finance)
- 财务数据: Financial Modeling Prep API (免费额度)

### 2. 基本面分析模块 (FundamentalAnalyzer)

```python
class FundamentalAnalyzer:
    - evaluate_business_model(company: Company) -> BusinessModelScore
    - check_financial_health(financials: FinancialData) -> HealthReport
    - calculate_valuation(metrics: Metrics) -> ValuationReport
    - screen_stocks(criteria: ScreenCriteria) -> List[Stock]
```

**筛选标准** (LEI框架):
- 年收入 > $100M
- 收入增长 15-20%
- 运营现金流 > 0
- 自由现金流 > 0

### 3. 技术分析模块 (TechnicalAnalyzer)

```python
class TechnicalAnalyzer:
    - calculate_ma(prices: Series, period: int) -> Series          # 均线
    - calculate_ema(prices: Series, period: int) -> Series        # 指数移动平均
    - calculate_deduction_price(prices: Series, period: int) -> Series  # 抵扣价
    - predict_ma_direction(prices: Series, period: int, days: int) -> Prediction  # 均线拐点预测
    - calculate_bias_ratio(price: float, ma: float) -> float       # 乖离率
    - detect_ma_concentration(ma_list: List[Series]) -> bool      # 均线密集检测
    - detect_2b_structure(prices: Series) -> bool                 # 2B结构识别
    - calculate_volume_profile(prices: Series, volumes: Series) -> VolumeProfile  # 成交量分布
```

**核心算法**:

#### 抵扣价推演
```python
def predict_ma_turn(prices: pd.DataFrame, ma_period: int = 60) -> dict:
    """
    推演均线拐点
    返回: {will_turn_up: bool, required_price: float, date: date}
    """
```

#### 2B结构检测
```python
def detect_2b_structure(prices: pd.Series) -> dict:
    """
    检测2B结构
    返回: {has_2b: bool, point_a: float, point_b: float, breakout: bool}
    """
```

### 4. 信号生成模块 (SignalGenerator)

```python
class SignalGenerator:
    - determine_clock_direction(prices: Series, volumes: Series) -> ClockDirection
    - generate_buy_signals(analysis: AnalysisReport) -> List[BuySignal]
    - generate_sell_signals(analysis: AnalysisReport) -> List[SellSignal]
    - calculate_risk_reward(entry: float, stop_loss: float, target: float) -> float
```

**信号类型**:
- `2B_STRUCTURE` - 2B结构信号
- `MA_CONCENTRATION_BREAKOUT` - 均线密集突破
- `MA_TURN_UP` - 均线拐头向上
- `BIAS_EXTREME` - 乖离率极端

### 5. 风险管理模块 (RiskManager)

```python
class RiskManager:
    - calculate_position_size(account_value: float, risk_per_trade: float, stop_loss: float) -> int
    - validate_trade(trade: Trade, rules: List[RiskRule]) -> ValidationResult
    - monitor_portfolio(positions: List[Position]) -> RiskReport
```

---

## API 设计

### 股票接口
```
GET  /api/stocks/search?q={query}              # 搜索股票
GET  /api/stocks/{symbol}                       # 获取股票基本信息
GET  /api/stocks/{symbol}/price                 # 获取实时价格
GET  /api/stocks/{symbol}/ohlcv                # 获取K线数据
GET  /api/stocks/{symbol}/financials           # 获取财务数据
```

### 分析接口
```
GET  /api/analysis/{symbol}/fundamental         # 基本面分析
GET  /api/analysis/{symbol}/technical          # 技术分析
GET  /api/analysis/{symbol}/full               # 完整分析
POST /api/analysis/screen                       # 股票筛选
```

### 信号接口
```
GET  /api/signals/{symbol}                      # 获取股票信号
GET  /api/signals/watchlist                     # 关注列表信号
GET  /api/signals/opportunities                 # 当前机会信号
```

### 模拟交易接口
```
POST  /api/trading/orders                      # 下单
GET   /api/trading/positions                   # 当前持仓
GET   /api/trading/orders                      # 订单历史
GET   /api/trading/portfolio                   # 投资组合报告
```

---

## 数据库设计

### 表结构

```sql
-- 股票基本信息
stocks (
    symbol VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    last_updated TIMESTAMP
)

-- 价格历史
price_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    date DATE,
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL,
    volume BIGINT,
    UNIQUE(symbol, date)
)

-- 财务数据
financials (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    period DATE,
    revenue BIGINT,
    revenue_growth DECIMAL,
    operating_cf BIGINT,
    free_cf BIGINT,
    ebit_margin DECIMAL,
    UNIQUE(symbol, period)
)

-- 信号记录
signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    signal_type VARCHAR(50),
    strength DECIMAL,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
)

-- 模拟交易
positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    quantity INT,
    entry_price DECIMAL,
    entry_date DATE,
    stop_loss DECIMAL,
    target_price DECIMAL
)
```

---

## 前端页面设计

### 1. 仪表盘 (Dashboard)
- 关注股票列表 + 实时信号
- 市场概览
- 今日机会

### 2. 股票详情页 (Stock Detail)
- K线图表 (支持均线、成交量)
- 基本面数据卡片
- 技术分析信号
- 买卖建议

### 3. 股票筛选页 (Screening)
- 自定义筛选条件
- 筛选结果列表
- 导出功能

### 4. 模拟交易页 (Paper Trading)
- 下单面板
- 持仓管理
- 交易历史
- 绩效报告

---

## 部署架构

```
开发环境:
  - 本地运行: FastAPI (localhost:8000) + React (localhost:3000)
  - 数据库: SQLite

生产环境:
  - 后端: Docker + Gunicorn + Uvicorn
  - 前端: Nginx
  - 数据库: PostgreSQL
  - 定时任务: APScheduler
```

---

## 开发计划

### MVP (2-3周)
1. 项目初始化
2. 数据获取 (yfinance)
3. 技术指标计算
4. 基础K线图表
5. 买卖信号生成

### V1.0 (1-2个月)
1. 基本面分析
2. 股票筛选
3. 用户认证
4. 模拟交易
5. 响应式UI

---

## 最后更新
2026-02-18
