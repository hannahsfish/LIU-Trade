import type { PositionItem } from '../api/client'
import { formatCurrency } from '../lib/utils'

interface Props {
  positions: PositionItem[]
}

export function AccountSummary({ positions }: Props) {
  const totalCost = positions.reduce((sum, p) => sum + p.entry_price * p.quantity, 0)
  const openCount = positions.length

  return (
    <div className="grid grid-cols-2 gap-4 mb-8 md:grid-cols-4">
      <SummaryCard label="持仓数量" value={`${openCount} 只`} />
      <SummaryCard label="持仓成本" value={formatCurrency(totalCost)} />
      <SummaryCard label="今日盈亏" value="--" sublabel="需行情数据" />
      <SummaryCard label="总市值" value="--" sublabel="需行情数据" />
    </div>
  )
}

function SummaryCard({ label, value, sublabel }: { label: string; value: string; sublabel?: string }) {
  return (
    <div className="rounded-xl p-5" style={{ backgroundColor: 'var(--color-surface)' }}>
      <div className="text-sm mb-1" style={{ color: 'var(--color-text-secondary)' }}>{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      {sublabel && <div className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>{sublabel}</div>}
    </div>
  )
}
