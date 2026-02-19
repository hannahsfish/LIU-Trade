import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type OHLCVBar, type MAData } from '../api/client'
import { StockChart } from '../components/StockChart'

export function Chart() {
  const { symbol } = useParams<{ symbol: string }>()
  const navigate = useNavigate()
  const [bars, setBars] = useState<OHLCVBar[]>([])
  const [mas, setMas] = useState<MAData[]>([])
  const [loading, setLoading] = useState(true)
  const [info, setInfo] = useState<{ last_price: number; bias_ratio_120: number | null } | null>(null)

  useEffect(() => {
    if (!symbol) return

    const load = async () => {
      setLoading(true)
      try {
        const [ohlcv, technical] = await Promise.all([
          api.getOHLCV(symbol),
          api.getTechnical(symbol),
        ])
        setBars(ohlcv.bars)
        setMas(technical.mas)
        setInfo({ last_price: technical.last_price, bias_ratio_120: technical.bias_ratio_120 })
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [symbol])

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate(-1)}
          className="px-3 py-1 rounded-lg text-sm"
          style={{ backgroundColor: 'var(--color-surface-hover)' }}
        >
          ← 返回
        </button>
        <h1 className="text-3xl font-bold">{symbol?.toUpperCase()}</h1>
        {info && (
          <span className="text-xl" style={{ color: 'var(--color-text-secondary)' }}>
            ${info.last_price}
          </span>
        )}
        {info?.bias_ratio_120 != null && (
          <span
            className="text-sm px-2 py-1 rounded"
            style={{
              backgroundColor: info.bias_ratio_120 > 50 ? 'var(--color-red-priority)' : 'var(--color-surface-hover)',
              color: info.bias_ratio_120 > 50 ? '#000' : 'var(--color-text-secondary)',
            }}
          >
            乖离率 {info.bias_ratio_120.toFixed(1)}%
          </span>
        )}
      </div>

      <div className="mb-4 flex gap-3 text-xs">
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5" style={{ backgroundColor: '#a855f7' }} /> MA20</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5" style={{ backgroundColor: '#3b82f6' }} /> MA60</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5" style={{ backgroundColor: '#f97316' }} /> EMA120</span>
      </div>

      {loading ? (
        <div className="text-center py-20" style={{ color: 'var(--color-text-secondary)' }}>加载中...</div>
      ) : bars.length === 0 ? (
        <div className="text-center py-20" style={{ color: 'var(--color-text-secondary)' }}>无数据</div>
      ) : (
        <StockChart bars={bars} mas={mas} />
      )}
    </div>
  )
}
