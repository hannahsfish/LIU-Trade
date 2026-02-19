import { useEffect, useState } from 'react'
import { api, type PositionItem } from '../api/client'
import { PositionCard } from '../components/PositionCard'

export function Positions() {
  const [positions, setPositions] = useState<PositionItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getPositions()
      .then(setPositions)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">持仓总览</h1>

      {loading ? (
        <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>加载中...</div>
      ) : positions.length === 0 ? (
        <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>
          暂无持仓。执行交易计划后将显示在此处。
        </div>
      ) : (
        positions.map((p) => <PositionCard key={p.id} position={p} />)
      )}
    </div>
  )
}
