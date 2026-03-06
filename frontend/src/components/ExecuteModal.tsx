import { useState } from 'react'
import type { CommandItem } from '../api/client'

interface Props {
  command: CommandItem
  brokerConnected: boolean
  onConfirm: (price: number, quantity: number, orderType: string) => void
  onCancel: () => void
}

export function ExecuteModal({ command, brokerConnected, onConfirm, onCancel }: Props) {
  const [price, setPrice] = useState(command.suggested_price?.toString() ?? '')
  const [quantity, setQuantity] = useState(command.suggested_quantity?.toString() ?? '')
  const [orderType, setOrderType] = useState<'LIMIT' | 'MARKET'>('LIMIT')

  const isMarket = brokerConnected && orderType === 'MARKET'

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const p = isMarket ? 0 : parseFloat(price)
    const q = parseInt(quantity, 10)
    if (isNaN(q) || q <= 0) return
    if (!isMarket && (isNaN(p) || p <= 0)) return
    onConfirm(p, q, brokerConnected ? orderType : 'LIMIT')
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}>
      <div className="rounded-2xl p-6 w-full max-w-md" style={{ backgroundColor: 'var(--color-surface)' }}>
        <h3 className="text-lg font-bold mb-1">
          {brokerConnected ? '委托下单' : '执行反馈'}
        </h3>
        <p className="text-sm mb-5" style={{ color: 'var(--color-text-secondary)' }}>{command.headline}</p>

        <form onSubmit={handleSubmit}>
          {brokerConnected && (
            <div className="flex gap-2 mb-4">
              {(['LIMIT', 'MARKET'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  className="flex-1 py-2 rounded-lg text-sm font-medium transition-colors"
                  style={{
                    backgroundColor: orderType === t ? 'var(--color-green-priority)' : 'var(--color-surface-hover)',
                    color: orderType === t ? '#000' : 'var(--color-text-secondary)',
                  }}
                  onClick={() => setOrderType(t)}
                >
                  {t === 'LIMIT' ? '限价单' : '市价单'}
                </button>
              ))}
            </div>
          )}

          <label className="block mb-4">
            <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              {brokerConnected ? '委托价格' : '实际成交价'}
            </span>
            <input
              type="number"
              step="0.01"
              value={isMarket ? '' : price}
              onChange={(e) => setPrice(e.target.value)}
              disabled={isMarket}
              placeholder={isMarket ? '市价单无需填写' : ''}
              className="block w-full mt-1 rounded-lg px-4 py-2 text-white outline-none disabled:opacity-40"
              style={{ backgroundColor: 'var(--color-bg)', border: '1px solid var(--color-border)' }}
            />
          </label>
          <label className="block mb-6">
            <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              {brokerConnected ? '委托数量' : '实际数量'}
            </span>
            <input
              type="number"
              step="1"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="block w-full mt-1 rounded-lg px-4 py-2 text-white outline-none"
              style={{ backgroundColor: 'var(--color-bg)', border: '1px solid var(--color-border)' }}
            />
          </label>
          <div className="flex gap-3">
            <button
              type="submit"
              className="flex-1 py-2 rounded-lg font-medium text-black"
              style={{ backgroundColor: 'var(--color-green-priority)' }}
            >
              {brokerConnected ? '提交委托' : '确认'}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 py-2 rounded-lg font-medium"
              style={{ backgroundColor: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)' }}
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
