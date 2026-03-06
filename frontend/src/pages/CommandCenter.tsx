import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type BrokerOrderItem, type BrokerStatus, type CommandItem, type PositionItem } from '../api/client'
import { AccountSummary } from '../components/AccountSummary'
import { CommandCard } from '../components/CommandCard'

export function CommandCenter() {
  const [commands, setCommands] = useState<CommandItem[]>([])
  const [positions, setPositions] = useState<PositionItem[]>([])
  const [brokerOrders, setBrokerOrders] = useState<BrokerOrderItem[]>([])
  const [loading, setLoading] = useState(true)
  const [broker, setBroker] = useState<BrokerStatus | null>(null)
  const [brokerLoading, setBrokerLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const brokerRef = useRef(broker)
  brokerRef.current = broker

  const refreshData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true)
    try {
      const fetches: [Promise<CommandItem[]>, Promise<PositionItem[]>, Promise<BrokerOrderItem[]>?] = [
        api.getCommands(),
        api.getPositions(),
      ]
      if (brokerRef.current?.connected) {
        fetches.push(api.getBrokerOrders())
      }
      const [cmds, pos, orders] = await Promise.all(fetches)
      setCommands(cmds)
      setPositions(pos)
      if (orders) setBrokerOrders(orders)
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [])

  const loadBrokerStatus = async () => {
    try {
      const status = await api.getBrokerStatus()
      setBroker(status)
    } catch {
      setBroker(null)
    }
  }

  useEffect(() => {
    const init = async () => {
      await loadBrokerStatus()
      await refreshData(true)
    }
    init()
  }, [refreshData])

  const hasSubmitting = commands.some((c) => c.status === 'SUBMITTING')

  useEffect(() => {
    if (hasSubmitting) {
      pollRef.current = setInterval(() => refreshData(), 3000)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [hasSubmitting, refreshData])

  const handleConnect = async () => {
    setBrokerLoading(true)
    try {
      await api.connectBroker()
      await loadBrokerStatus()
    } catch (err) {
      console.error('Broker connect failed:', err)
    } finally {
      setBrokerLoading(false)
    }
  }

  const handleDisconnect = async () => {
    setBrokerLoading(true)
    try {
      await api.disconnectBroker()
      await loadBrokerStatus()
    } catch (err) {
      console.error('Broker disconnect failed:', err)
    } finally {
      setBrokerLoading(false)
    }
  }

  const handleExecute = async (id: number, price: number, qty: number, orderType: string) => {
    await api.executeCommand(id, price, qty, orderType)
    refreshData()
    if (brokerRef.current?.connected) loadBrokerStatus()
  }

  const handleDismiss = async (id: number) => {
    await api.dismissCommand(id)
    setCommands((prev) => prev.filter((c) => c.id !== id))
  }

  const handleCancelOrder = async (brokerOrderId: number) => {
    try {
      await api.cancelBrokerOrder(brokerOrderId)
      refreshData()
    } catch (err) {
      console.error('Cancel order failed:', err)
    }
  }

  const brokerConnected = broker?.connected ?? false

  const brokerOrderByCommandId = (commandId: number): BrokerOrderItem | undefined =>
    brokerOrders.find((o) => o.command_id === commandId && (o.status === 'SUBMITTED' || o.status === 'PARTIAL'))

  const redCommands = commands.filter((c) => c.priority === 'RED')
  const yellowCommands = commands.filter((c) => c.priority === 'YELLOW')
  const greenCommands = commands.filter((c) => c.priority === 'GREEN')

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">指令面板</h1>
        <div className="flex items-center gap-3">
          <span
            className="inline-block w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: broker?.connected ? 'var(--color-green-priority)' : 'var(--color-text-secondary)' }}
          />
          <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            {broker?.connected ? `${broker.trd_env}` : '券商未连接'}
          </span>
          {broker?.connected ? (
            <button
              className="px-3 py-1 rounded-lg text-xs"
              style={{ backgroundColor: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)' }}
              onClick={handleDisconnect}
              disabled={brokerLoading}
            >
              断开
            </button>
          ) : (
            <button
              className="px-3 py-1 rounded-lg text-xs font-medium text-black"
              style={{ backgroundColor: 'var(--color-green-priority)' }}
              onClick={handleConnect}
              disabled={brokerLoading}
            >
              {brokerLoading ? '连接中...' : '连接券商'}
            </button>
          )}
        </div>
      </div>

      <AccountSummary positions={positions} />

      {brokerConnected && broker?.account && (
        <div
          className="rounded-xl p-4 mb-6 flex gap-6 text-sm"
          style={{ backgroundColor: 'var(--color-surface)' }}
        >
          <div>
            <span style={{ color: 'var(--color-text-secondary)' }}>总资产</span>
            <span className="ml-2 font-medium">${broker.account.total_assets.toLocaleString()}</span>
          </div>
          <div>
            <span style={{ color: 'var(--color-text-secondary)' }}>现金</span>
            <span className="ml-2 font-medium">${broker.account.cash.toLocaleString()}</span>
          </div>
          <div>
            <span style={{ color: 'var(--color-text-secondary)' }}>购买力</span>
            <span className="ml-2 font-medium">${broker.account.buying_power.toLocaleString()}</span>
          </div>
          <div>
            <span style={{ color: 'var(--color-text-secondary)' }}>持仓市值</span>
            <span className="ml-2 font-medium">${broker.account.market_value.toLocaleString()}</span>
          </div>
        </div>
      )}

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
                <CommandCard
                  key={c.id}
                  command={c}
                  brokerConnected={brokerConnected}
                  brokerOrder={brokerOrderByCommandId(c.id)}
                  onExecute={handleExecute}
                  onDismiss={handleDismiss}
                  onCancelOrder={handleCancelOrder}
                />
              ))}
            </section>
          )}

          {yellowCommands.length > 0 && (
            <section className="mb-6">
              <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--color-yellow-priority)' }}>
                需要关注
              </h2>
              {yellowCommands.map((c) => (
                <CommandCard
                  key={c.id}
                  command={c}
                  brokerConnected={brokerConnected}
                  brokerOrder={brokerOrderByCommandId(c.id)}
                  onExecute={handleExecute}
                  onDismiss={handleDismiss}
                  onCancelOrder={handleCancelOrder}
                />
              ))}
            </section>
          )}

          {greenCommands.length > 0 && (
            <section className="mb-6">
              <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--color-green-priority)' }}>
                持仓正常
              </h2>
              {greenCommands.map((c) => (
                <CommandCard
                  key={c.id}
                  command={c}
                  brokerConnected={brokerConnected}
                  brokerOrder={brokerOrderByCommandId(c.id)}
                  onExecute={handleExecute}
                  onDismiss={handleDismiss}
                  onCancelOrder={handleCancelOrder}
                />
              ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}
