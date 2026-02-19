import { useEffect, useState } from 'react'
import { api, type CommandItem, type PositionItem } from '../api/client'
import { AccountSummary } from '../components/AccountSummary'
import { CommandCard } from '../components/CommandCard'

export function CommandCenter() {
  const [commands, setCommands] = useState<CommandItem[]>([])
  const [positions, setPositions] = useState<PositionItem[]>([])
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [cmds, pos] = await Promise.all([api.getCommands(), api.getPositions()])
      setCommands(cmds)
      setPositions(pos)
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleExecute = async (id: number, price: number, qty: number) => {
    await api.executeCommand(id, price, qty)
    loadData()
  }

  const handleDismiss = async (id: number) => {
    await api.dismissCommand(id)
    setCommands((prev) => prev.filter((c) => c.id !== id))
  }

  const redCommands = commands.filter((c) => c.priority === 'RED')
  const yellowCommands = commands.filter((c) => c.priority === 'YELLOW')
  const greenCommands = commands.filter((c) => c.priority === 'GREEN')

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">指令面板</h1>

      <AccountSummary positions={positions} />

      {loading ? (
        <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>加载中...</div>
      ) : commands.length === 0 ? (
        <div className="text-center py-12" style={{ color: 'var(--color-text-secondary)' }}>
          暂无指令。添加股票到关注列表以开始扫描。
        </div>
      ) : (
        <>
          {redCommands.length > 0 && (
            <section className="mb-6">
              <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--color-red-priority)' }}>
                需要立即执行
              </h2>
              {redCommands.map((c) => (
                <CommandCard key={c.id} command={c} onExecute={handleExecute} onDismiss={handleDismiss} />
              ))}
            </section>
          )}

          {yellowCommands.length > 0 && (
            <section className="mb-6">
              <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--color-yellow-priority)' }}>
                需要关注
              </h2>
              {yellowCommands.map((c) => (
                <CommandCard key={c.id} command={c} onExecute={handleExecute} onDismiss={handleDismiss} />
              ))}
            </section>
          )}

          {greenCommands.length > 0 && (
            <section className="mb-6">
              <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--color-green-priority)' }}>
                持仓正常
              </h2>
              {greenCommands.map((c) => (
                <CommandCard key={c.id} command={c} onExecute={handleExecute} onDismiss={handleDismiss} />
              ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}
