import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type WatchlistItem, type ScannerStatus } from '../api/client'
import { formatCurrency } from '../lib/utils'

export function Opportunities() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [status, setStatus] = useState<ScannerStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [addSymbol, setAddSymbol] = useState('')
  const navigate = useNavigate()

  const loadData = useCallback(async () => {
    try {
      const [wl, st] = await Promise.all([api.getWatchlist(), api.getScannerStatus()])
      setWatchlist(wl)
      setStatus(st)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  useEffect(() => {
    if (!status?.running) return
    const interval = setInterval(async () => {
      const st = await api.getScannerStatus()
      setStatus(st)
      if (!st.running) {
        clearInterval(interval)
        loadData()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [status?.running, loadData])

  const handleScan = async (full: boolean) => {
    await api.triggerScan(full)
    const st = await api.getScannerStatus()
    setStatus(st)
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!addSymbol.trim()) return
    await api.addToWatchlist(addSymbol.trim())
    setAddSymbol('')
    loadData()
  }

  const handleRemove = async (symbol: string) => {
    await api.removeFromWatchlist(symbol)
    setWatchlist(prev => prev.filter(w => w.symbol !== symbol))
  }

  const handleCreatePlan = (item: WatchlistItem) => {
    const sig = item.latest_signal
    if (!sig) return
    api.createPlan({
      symbol: item.symbol,
      expectation: sig.reasoning,
      clock_direction: '2_OCLOCK',
      target_price: sig.target_price,
      stop_loss: sig.stop_loss,
      stop_loss_type: 'PREV_LOW',
      max_loss_pct: Math.round(((sig.entry_price - sig.stop_loss) / sig.entry_price) * 100 * 100) / 100,
      entry_price: sig.entry_price,
      position_type: sig.position_advice,
      risk_reward_ratio: sig.risk_reward_ratio,
      signal_type: sig.signal_type,
      signal_reasoning: sig.reasoning,
    }).then(() => navigate('/'))
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">机会雷达</h1>
        <div className="flex gap-2">
          <button
            onClick={() => handleScan(false)}
            disabled={status?.running}
            className="px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
            style={{ backgroundColor: 'var(--color-surface-hover)' }}
          >
            {status?.running ? `扫描中 (${status.current_symbol})...` : '日常扫描'}
          </button>
          <button
            onClick={() => handleScan(true)}
            disabled={status?.running}
            className="px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
            style={{ backgroundColor: 'var(--color-yellow-priority)', color: '#000' }}
          >
            全量扫描
          </button>
        </div>
      </div>

      {status && (
        <div className="rounded-xl p-4 mb-6 grid grid-cols-2 gap-x-8 gap-y-2 text-sm" style={{ backgroundColor: 'var(--color-surface)' }}>
          <div style={{ color: 'var(--color-text-secondary)' }}>
            上次扫描: {status.last_scan_time ? new Date(status.last_scan_time).toLocaleString('zh-CN') : '从未'}
          </div>
          <div style={{ color: 'var(--color-text-secondary)' }}>
            耗时: {status.last_scan_duration_seconds}s | 已扫描: {status.stocks_scanned}
          </div>
          <div style={{ color: 'var(--color-text-secondary)' }}>
            发现机会: {status.opportunities_found} | 错误: {status.errors}
          </div>
          <div style={{ color: 'var(--color-text-secondary)' }}>
            API 余量: {status.api_budget.remaining_this_minute}/min | 累计: {status.api_budget.total_calls}
          </div>
        </div>
      )}

      <form onSubmit={handleAdd} className="flex gap-3 mb-6">
        <input
          type="text"
          value={addSymbol}
          onChange={(e) => setAddSymbol(e.target.value)}
          placeholder="手动添加股票代码"
          className="flex-1 rounded-xl px-4 py-2 outline-none text-white text-sm"
          style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
        />
        <button type="submit" className="px-4 py-2 rounded-xl text-sm" style={{ backgroundColor: 'var(--color-surface-hover)' }}>
          添加
        </button>
      </form>

      <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--color-text-secondary)' }}>
        关注列表 ({watchlist.length})
      </h2>

      {loading ? (
        <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>加载中...</div>
      ) : watchlist.length === 0 ? (
        <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>
          关注列表为空。点击「日常扫描」自动发现机会，或手动添加股票代码。
        </div>
      ) : (
        watchlist.map((item) => (
          <WatchlistCard
            key={item.symbol}
            item={item}
            onRemove={handleRemove}
            onCreatePlan={handleCreatePlan}
            onViewChart={(s) => navigate(`/chart/${s}`)}
          />
        ))
      )}
    </div>
  )
}

function WatchlistCard({ item, onRemove, onCreatePlan, onViewChart }: {
  item: WatchlistItem
  onRemove: (s: string) => void
  onCreatePlan: (item: WatchlistItem) => void
  onViewChart: (s: string) => void
}) {
  const sig = item.latest_signal
  const isStrong = sig?.position_advice === 'CONFIRM'

  return (
    <div className="rounded-xl p-5 mb-3" style={{ backgroundColor: 'var(--color-surface)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold cursor-pointer hover:underline" onClick={() => onViewChart(item.symbol)}>
            {item.symbol}
          </span>
          {sig && (
            <span
              className="text-xs font-bold px-2 py-0.5 rounded"
              style={{
                backgroundColor: isStrong ? 'var(--color-green-priority)' : 'var(--color-yellow-priority)',
                color: '#000',
              }}
            >
              {isStrong ? '重仓机会' : '试探机会'}
            </span>
          )}
          <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{item.notes}</span>
        </div>
        <button
          onClick={() => onRemove(item.symbol)}
          className="text-xs px-2 py-1 rounded"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          移除
        </button>
      </div>

      {sig ? (
        <>
          <div className="grid grid-cols-4 gap-4 text-sm mb-3">
            <div>
              <span style={{ color: 'var(--color-text-secondary)' }}>信号</span>
              <div className="font-medium text-xs">{sig.signal_type.replace(/_/g, ' ')}</div>
            </div>
            <div>
              <span style={{ color: 'var(--color-text-secondary)' }}>入场</span>
              <div className="font-medium">{formatCurrency(sig.entry_price)}</div>
            </div>
            <div>
              <span style={{ color: 'var(--color-text-secondary)' }}>止损</span>
              <div className="font-medium" style={{ color: 'var(--color-red-priority)' }}>{formatCurrency(sig.stop_loss)}</div>
            </div>
            <div>
              <span style={{ color: 'var(--color-text-secondary)' }}>盈亏比</span>
              <div className="font-medium">{sig.risk_reward_ratio}:1</div>
            </div>
          </div>
          <p className="text-xs leading-relaxed mb-3" style={{ color: 'var(--color-text-secondary)' }}>{sig.reasoning}</p>
          <button
            className="w-full py-2 rounded-lg font-medium text-sm text-black"
            style={{ backgroundColor: isStrong ? 'var(--color-green-priority)' : 'var(--color-yellow-priority)' }}
            onClick={() => onCreatePlan(item)}
          >
            创建交易计划
          </button>
        </>
      ) : (
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>暂无信号，等待下次扫描...</p>
      )}
    </div>
  )
}
