import { useNavigate } from 'react-router-dom'
import type { PositionItem } from '../api/client'
import { formatCurrency, formatPercent } from '../lib/utils'

interface Props {
  position: PositionItem
}

export function PositionCard({ position }: Props) {
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
          style={{ color: position.pnl_pct && position.pnl_pct >= 0 ? 'var(--color-green-priority)' : 'var(--color-red-priority)' }}
        >
          {position.pnl_pct != null ? formatPercent(position.pnl_pct) : '--'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>成本</span>
          <div className="font-medium">{formatCurrency(position.entry_price)}</div>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>止损</span>
          <div className="font-medium" style={{ color: 'var(--color-red-priority)' }}>
            {formatCurrency(position.stop_loss)}
          </div>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>目标</span>
          <div className="font-medium" style={{ color: 'var(--color-green-priority)' }}>
            {formatCurrency(position.target_price)}
          </div>
        </div>
      </div>
    </div>
  )
}
