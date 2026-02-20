import type { PositionItem } from '../api/client'
import { formatCurrency } from '../lib/utils'

interface Props {
  positions: PositionItem[]
}

export function AccountSummary({ positions }: Props) {
  const totalCost = positions.reduce((sum, p) => sum + p.entry_price * p.quantity, 0)
  const openCount = positions.length

  const hasCurrentPrice = positions.some(p => p.current_price != null)
  const totalPnl = hasCurrentPrice
    ? positions.reduce((sum, p) => sum + (p.pnl ?? 0), 0)
    : null
  const totalMarketValue = hasCurrentPrice
    ? positions.reduce((sum, p) => sum + (p.current_price ?? p.entry_price) * p.quantity, 0)
    : null

  const pnlColor = totalPnl != null && totalPnl >= 0 ? 'var(--color-green-priority)' : 'var(--color-red-priority)'

  return (
    <div className="grid grid-cols-2 gap-4 mb-8 md:grid-cols-4">
      <SummaryCard label="持仓数量" value={`${openCount} 只`} />
      <SummaryCard label="持仓成本" value={formatCurrency(totalCost)} />
      <SummaryCard
        label="浮动盈亏"
        value={totalPnl != null ? `${totalPnl >= 0 ? '+' : ''}${formatCurrency(totalPnl)}` : '--'}
        valueColor={totalPnl != null ? pnlColor : undefined}
      />
      <SummaryCard
        label="总市值"
        value={totalMarketValue != null ? formatCurrency(totalMarketValue) : '--'}
      />
    </div>
  )
}

function SummaryCard({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div className="rounded-xl p-5" style={{ backgroundColor: 'var(--color-surface)' }}>
      <div className="text-sm mb-1" style={{ color: 'var(--color-text-secondary)' }}>{label}</div>
      <div className="text-2xl font-bold" style={valueColor ? { color: valueColor } : undefined}>{value}</div>
    </div>
  )
}
