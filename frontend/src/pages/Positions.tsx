import { useEffect, useState } from 'react'
import { api, type PositionItem, type BrokerPositionItem } from '../api/client'
import { PositionCard } from '../components/PositionCard'
import { BrokerPositionCard } from '../components/BrokerPositionCard'
import { formatCurrency, formatPercent } from '../lib/utils'

export function Positions() {
  const [positions, setPositions] = useState<PositionItem[]>([])
  const [brokerPositions, setBrokerPositions] = useState<BrokerPositionItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getPositions().catch(() => [] as PositionItem[]),
      api.getBrokerPositions().catch(() => [] as BrokerPositionItem[]),
    ])
      .then(([pos, broker]) => {
        setPositions(pos)
        setBrokerPositions(broker)
      })
      .finally(() => setLoading(false))
  }, [])

  const brokerTotal = brokerPositions.reduce((sum, p) => sum + p.market_value, 0)
  const brokerTotalCost = brokerPositions.reduce((sum, p) => sum + p.cost_price * p.quantity, 0)
  const brokerTotalPnl = brokerPositions.reduce((sum, p) => sum + p.unrealized_pnl, 0)

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">持仓总览</h1>

      {loading ? (
        <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>加载中...</div>
      ) : (
        <>
          {brokerPositions.length > 0 && (
            <div className="mb-8">
              <h2 className="text-xl font-bold mb-4">券商持仓</h2>
              <div className="grid grid-cols-2 gap-4 mb-4 md:grid-cols-4">
                <SummaryCard label="持仓数量" value={`${brokerPositions.length} 只`} />
                <SummaryCard label="持仓成本" value={formatCurrency(brokerTotalCost)} />
                <SummaryCard
                  label="浮动盈亏"
                  value={`${brokerTotalPnl >= 0 ? '+' : ''}${formatCurrency(brokerTotalPnl)}`}
                  valueColor={brokerTotalPnl >= 0 ? 'var(--color-green-priority)' : 'var(--color-red-priority)'}
                />
                <SummaryCard label="总市值" value={formatCurrency(brokerTotal)} />
              </div>
              {brokerPositions.map((p) => (
                <BrokerPositionCard key={p.symbol} position={p} />
              ))}
            </div>
          )}

          {positions.length > 0 && (
            <div>
              <h2 className="text-xl font-bold mb-4">系统持仓</h2>
              {positions.map((p) => <PositionCard key={p.id} position={p} />)}
            </div>
          )}

          {brokerPositions.length === 0 && positions.length === 0 && (
            <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>
              暂无持仓。执行交易计划后将显示在此处。
            </div>
          )}
        </>
      )}
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
