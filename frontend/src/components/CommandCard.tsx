import { useState } from 'react'
import type { BrokerOrderItem, CommandItem } from '../api/client'
import { priorityColor, priorityLabel } from '../lib/utils'
import { ExecuteModal } from './ExecuteModal'

interface Props {
  command: CommandItem
  brokerConnected: boolean
  brokerOrder?: BrokerOrderItem
  onExecute: (id: number, price: number, qty: number, orderType: string) => void
  onDismiss: (id: number) => void
  onCancelOrder?: (brokerOrderId: number) => void
}

export function CommandCard({ command, brokerConnected, brokerOrder, onExecute, onDismiss, onCancelOrder }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [showModal, setShowModal] = useState(false)

  const isSubmitting = command.status === 'SUBMITTING'
  const isActionable = command.action === 'BUY' || command.action === 'SELL' || command.action === 'STOP_LOSS'

  return (
    <>
      <div
        className="rounded-xl p-5 mb-3 cursor-pointer transition-colors"
        style={{ backgroundColor: 'var(--color-surface)', borderLeft: `4px solid ${priorityColor(command.priority)}` }}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <span
              className="text-xs font-bold px-2 py-1 rounded shrink-0"
              style={{ backgroundColor: priorityColor(command.priority), color: '#000' }}
            >
              {priorityLabel(command.priority)}
            </span>
            <span className="font-medium truncate">{command.headline}</span>
          </div>
          <div className="flex gap-2 shrink-0 ml-4">
            {isSubmitting ? (
              <>
                <span
                  className="px-3 py-1 rounded-lg text-sm font-medium animate-pulse"
                  style={{ backgroundColor: 'var(--color-surface-hover)', color: 'var(--color-yellow-priority)' }}
                >
                  下单中...
                </span>
                {brokerOrder && onCancelOrder && (
                  <button
                    className="px-3 py-1 rounded-lg text-sm"
                    style={{ backgroundColor: 'var(--color-surface-hover)', color: 'var(--color-red-priority)' }}
                    onClick={(e) => { e.stopPropagation(); onCancelOrder(brokerOrder.id) }}
                  >
                    撤单
                  </button>
                )}
              </>
            ) : isActionable ? (
              <button
                className="px-3 py-1 rounded-lg text-sm font-medium text-black"
                style={{ backgroundColor: priorityColor(command.priority) }}
                onClick={(e) => { e.stopPropagation(); setShowModal(true) }}
              >
                执行下单
              </button>
            ) : null}
            {!isSubmitting && (
              <button
                className="px-3 py-1 rounded-lg text-sm"
                style={{ backgroundColor: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)' }}
                onClick={(e) => { e.stopPropagation(); onDismiss(command.id) }}
              >
                忽略
              </button>
            )}
          </div>
        </div>

        {isSubmitting && brokerOrder && (
          <div className="mt-3 flex gap-4 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <span>订单号: {brokerOrder.futu_order_id}</span>
            <span>{brokerOrder.order_type === 'MARKET' ? '市价' : `限价 $${brokerOrder.price}`}</span>
            <span>{brokerOrder.side === 'BUY' ? '买入' : '卖出'} x {brokerOrder.quantity}</span>
            {(brokerOrder.filled_quantity ?? 0) > 0 && (
              <span style={{ color: 'var(--color-green-priority)' }}>
                已成交 {brokerOrder.filled_quantity} @ ${brokerOrder.filled_price}
              </span>
            )}
          </div>
        )}

        {expanded && command.detail && (
          <div className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            {command.detail}
          </div>
        )}
      </div>

      {showModal && (
        <ExecuteModal
          command={command}
          brokerConnected={brokerConnected}
          onConfirm={(price, qty, orderType) => {
            onExecute(command.id, price, qty, orderType)
            setShowModal(false)
          }}
          onCancel={() => setShowModal(false)}
        />
      )}
    </>
  )
}
