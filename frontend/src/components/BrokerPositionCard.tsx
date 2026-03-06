import { useNavigate } from 'react-router-dom'
import type { BrokerPositionItem } from '../api/client'
import { formatCurrency, formatPercent } from '../lib/utils'

interface Props {
  position: BrokerPositionItem
}

export function BrokerPositionCard({ position }: Props) {
  const navigate = useNavigate()

  return (
    <div
      className="rounded-xl p-5 mb-3 cursor-pointer transition-colors hover:brightness-110"
      style={{ backgroundColor: 'var(--color-surface)' }}
      onClick={() => navigate(`/chart/${position.symbol}`)}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold">{position.symbol}</span>
          <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            {position.quantity}股
          </span>
        </div>
        <span
          className="text-lg font-bold"
          style={{ color: position.unrealized_pnl >= 0 ? 'var(--color-green-priority)' : 'var(--color-red-priority)' }}
        >
          {formatPercent(position.unrealized_pnl_pct)}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4 text-sm">
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>成本</span>
          <div className="font-medium">{formatCurrency(position.cost_price)}</div>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>现价</span>
          <div className="font-medium">{formatCurrency(position.market_value / position.quantity)}</div>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>市值</span>
          <div className="font-medium">{formatCurrency(position.market_value)}</div>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>盈亏</span>
          <div
            className="font-medium"
            style={{ color: position.unrealized_pnl >= 0 ? 'var(--color-green-priority)' : 'var(--color-red-priority)' }}
          >
            {position.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(position.unrealized_pnl)}
          </div>
        </div>
      </div>
    </div>
  )
}
