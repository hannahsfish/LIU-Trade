import type { BuySignal } from '../api/client'
import { formatCurrency } from '../lib/utils'

interface Props {
  signal: BuySignal
  onCreatePlan: (signal: BuySignal) => void
}

export function OpportunityCard({ signal, onCreatePlan }: Props) {
  const isStrong = signal.position_advice === 'CONFIRM'

  return (
    <div className="rounded-xl p-5 mb-3" style={{ backgroundColor: 'var(--color-surface)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span
            className="text-xs font-bold px-2 py-1 rounded"
            style={{
              backgroundColor: isStrong ? 'var(--color-green-priority)' : 'var(--color-yellow-priority)',
              color: '#000',
            }}
          >
            {isStrong ? '强' : '弱'}
          </span>
          <span className="font-medium">{signal.signal_type.replace(/_/g, ' ')}</span>
        </div>
        <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          盈亏比 {signal.risk_reward_ratio}:1
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm mb-3">
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>入场</span>
          <div className="font-medium">{formatCurrency(signal.entry_price)}</div>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>止损</span>
          <div className="font-medium" style={{ color: 'var(--color-red-priority)' }}>
            {formatCurrency(signal.stop_loss)}
          </div>
        </div>
        <div>
          <span style={{ color: 'var(--color-text-secondary)' }}>目标</span>
          <div className="font-medium" style={{ color: 'var(--color-green-priority)' }}>
            {formatCurrency(signal.target_price)}
          </div>
        </div>
      </div>

      <p className="text-sm leading-relaxed mb-4" style={{ color: 'var(--color-text-secondary)' }}>
        {signal.reasoning}
      </p>

      <button
        className="w-full py-2 rounded-lg font-medium text-sm"
        style={{ backgroundColor: 'var(--color-surface-hover)' }}
        onClick={() => onCreatePlan(signal)}
      >
        创建交易计划
      </button>
    </div>
  )
}
