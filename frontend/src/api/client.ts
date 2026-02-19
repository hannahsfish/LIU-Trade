const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

export interface OHLCVBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface OHLCVResponse {
  symbol: string
  interval: string
  bars: OHLCVBar[]
}

export interface StockSearchResult {
  symbol: string
  name: string | null
  sector: string | null
  industry: string | null
  market_cap: number | null
}

export interface MAData {
  date: string
  ma20: number | null
  ma60: number | null
  ema120: number | null
}

export interface TechnicalAnalysis {
  symbol: string
  last_price: number
  last_date: string
  mas: MAData[]
  bias_ratio_120: number | null
  two_b_signal: unknown | null
  ma_concentration: unknown | null
}

export interface BuySignal {
  signal_type: string
  position_advice: string
  entry_price: number
  stop_loss: number
  target_price: number
  risk_reward_ratio: number
  reasoning: string
}

export interface CommandItem {
  id: number
  symbol: string
  priority: string
  action: string
  headline: string
  detail: string | null
  suggested_price: number | null
  suggested_quantity: number | null
  stop_loss: number | null
  target_price: number | null
  risk_reward_ratio: number | null
  status: string
  created_at: string
}

export interface PlanItem {
  id: number
  symbol: string
  expectation: string
  clock_direction: string
  target_price: number
  stop_loss: number
  stop_loss_type: string
  max_loss_pct: number
  entry_price: number
  position_type: string
  position_size: number | null
  risk_reward_ratio: number
  status: string
  signal_type: string | null
  signal_reasoning: string | null
  created_at: string
}

export interface PositionItem {
  id: number
  plan_id: number | null
  symbol: string
  quantity: number
  entry_price: number
  entry_date: string
  stop_loss: number
  target_price: number
  current_price: number | null
  pnl: number | null
  pnl_pct: number | null
  status: string
}

export interface ScannerStatus {
  running: boolean
  current_symbol: string
  last_scan_time: string | null
  last_scan_duration_seconds: number
  stocks_scanned: number
  opportunities_found: number
  watchlist_added: number
  watchlist_removed: number
  errors: number
  api_budget: { total_calls: number; remaining_this_minute: number; total_waits: number }
}

export interface WatchlistItem {
  symbol: string
  added_at: string | null
  notes: string | null
  latest_signal: BuySignal & { strength: number; created_at: string } | null
}

export const api = {
  searchStocks: (q: string) =>
    request<StockSearchResult[]>(`/stocks/search?q=${encodeURIComponent(q)}`),

  getOHLCV: (symbol: string, interval = 'daily') =>
    request<OHLCVResponse>(`/stocks/${symbol}/ohlcv?interval=${interval}`),

  getTechnical: (symbol: string) =>
    request<TechnicalAnalysis>(`/analysis/${symbol}/technical`),

  getBuySignals: (symbol: string) =>
    request<BuySignal[]>(`/signals/${symbol}/buy`),

  getOpportunities: () =>
    request<BuySignal[]>(`/signals/opportunities`),

  getCommands: () =>
    request<CommandItem[]>(`/commands`),

  executeCommand: (id: number, actual_price: number, actual_quantity: number) =>
    request(`/commands/${id}/execute`, {
      method: 'POST',
      body: JSON.stringify({ actual_price, actual_quantity }),
    }),

  dismissCommand: (id: number) =>
    request(`/commands/${id}/dismiss`, { method: 'POST' }),

  getPlans: () =>
    request<PlanItem[]>(`/plans`),

  createPlan: (data: Record<string, unknown>) =>
    request<PlanItem>(`/plans`, { method: 'POST', body: JSON.stringify(data) }),

  executePlan: (id: number, actual_price: number, actual_quantity: number) =>
    request(`/plans/${id}/execute`, {
      method: 'POST',
      body: JSON.stringify({ actual_price, actual_quantity }),
    }),

  getPositions: (status = 'OPEN') =>
    request<PositionItem[]>(`/positions?status=${status}`),

  closePosition: (id: number, exit_price: number, exit_reason: string) =>
    request(`/positions/${id}/close`, {
      method: 'POST',
      body: JSON.stringify({ exit_price, exit_reason }),
    }),

  getScannerStatus: () =>
    request<ScannerStatus>(`/scanner/status`),

  triggerScan: (full = false) =>
    request<{ message: string }>(`/scanner/run?full=${full}`, { method: 'POST' }),

  getWatchlist: () =>
    request<WatchlistItem[]>(`/scanner/watchlist`),

  addToWatchlist: (symbol: string) =>
    request(`/scanner/watchlist/${symbol}`, { method: 'POST' }),

  removeFromWatchlist: (symbol: string) =>
    request(`/scanner/watchlist/${symbol}`, { method: 'DELETE' }),
}
