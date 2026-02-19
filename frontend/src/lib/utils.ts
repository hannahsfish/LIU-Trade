export function formatCurrency(value: number): string {
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

export function priorityColor(priority: string): string {
  switch (priority) {
    case 'RED':
      return 'var(--color-red-priority)'
    case 'YELLOW':
      return 'var(--color-yellow-priority)'
    case 'GREEN':
      return 'var(--color-green-priority)'
    default:
      return 'var(--color-text-secondary)'
  }
}

export function priorityLabel(priority: string): string {
  switch (priority) {
    case 'RED':
      return '红'
    case 'YELLOW':
      return '黄'
    case 'GREEN':
      return '绿'
    default:
      return priority
  }
}
