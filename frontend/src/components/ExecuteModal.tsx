import { useState } from 'react'
import type { CommandItem } from '../api/client'

interface Props {
  command: CommandItem
  onConfirm: (price: number, quantity: number) => void
  onCancel: () => void
}

export function ExecuteModal({ command, onConfirm, onCancel }: Props) {
  const [price, setPrice] = useState(command.suggested_price?.toString() ?? '')
  const [quantity, setQuantity] = useState(command.suggested_quantity?.toString() ?? '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const p = parseFloat(price)
    const q = parseInt(quantity, 10)
    if (!isNaN(p) && !isNaN(q) && p > 0 && q > 0) {
      onConfirm(p, q)
    }
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}>
      <div className="rounded-2xl p-6 w-full max-w-md" style={{ backgroundColor: 'var(--color-surface)' }}>
        <h3 className="text-lg font-bold mb-1">执行反馈</h3>
        <p className="text-sm mb-5" style={{ color: 'var(--color-text-secondary)' }}>{command.headline}</p>

        <form onSubmit={handleSubmit}>
          <label className="block mb-4">
            <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>实际成交价</span>
            <input
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="block w-full mt-1 rounded-lg px-4 py-2 text-white outline-none"
              style={{ backgroundColor: 'var(--color-bg)', border: '1px solid var(--color-border)' }}
            />
          </label>
          <label className="block mb-6">
            <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>实际数量</span>
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
              确认
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
