import { useState } from 'react'
import type { CommandItem } from '../api/client'
import { priorityColor, priorityLabel } from '../lib/utils'
import { ExecuteModal } from './ExecuteModal'

interface Props {
  command: CommandItem
  onExecute: (id: number, price: number, qty: number) => void
  onDismiss: (id: number) => void
}

export function CommandCard({ command, onExecute, onDismiss }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [showModal, setShowModal] = useState(false)

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
            {command.action === 'BUY' || command.action === 'SELL' || command.action === 'STOP_LOSS' ? (
              <button
                className="px-3 py-1 rounded-lg text-sm font-medium text-black"
                style={{ backgroundColor: priorityColor(command.priority) }}
                onClick={(e) => { e.stopPropagation(); setShowModal(true) }}
              >
                已执行
              </button>
            ) : null}
            <button
              className="px-3 py-1 rounded-lg text-sm"
              style={{ backgroundColor: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)' }}
              onClick={(e) => { e.stopPropagation(); onDismiss(command.id) }}
            >
              忽略
            </button>
          </div>
        </div>

        {expanded && command.detail && (
          <div className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            {command.detail}
          </div>
        )}
      </div>

      {showModal && (
        <ExecuteModal
          command={command}
          onConfirm={(price, qty) => {
            onExecute(command.id, price, qty)
            setShowModal(false)
          }}
          onCancel={() => setShowModal(false)}
        />
      )}
    </>
  )
}
