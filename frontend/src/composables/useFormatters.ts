// Number/time formatting helpers duplicated near-verbatim across AgentCard,
// AgentStatusPill, AgentDetailView, DashboardView, and every agent overview tab.

export function formatPnL(value: number | null | undefined): string {
  const v = value ?? 0
  const sign = v >= 0 ? '+' : ''
  return `${sign}$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatCompact(value: number | null | undefined): string {
  const v = value ?? 0
  if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M'
  if (v >= 1000) return (v / 1000).toFixed(1) + 'K'
  return v.toString()
}

export function formatUptime(startedAt: string | null | undefined): string {
  if (!startedAt) return '—'
  const diff = Date.now() - new Date(startedAt).getTime()
  if (diff < 60000) return `${Math.floor(diff / 1000)}s`
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return `${Math.floor(diff / 86400000)}d`
}

export function formatDuration(ms: number | null | undefined): string {
  if (!ms) return '—'
  if (ms < 60000) return `${Math.floor(ms / 1000)}s`
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m`
  if (ms < 86400000) return `${Math.floor(ms / 3600000)}h`
  return `${Math.floor(ms / 86400000)}d`
}

export function formatRelativeTime(timestamp: number | string | null | undefined): string {
  if (!timestamp) return '—'
  const t = typeof timestamp === 'string' ? new Date(timestamp).getTime() : timestamp
  const diff = Date.now() - t
  if (diff < 0) return 'just now'
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return new Date(t).toLocaleDateString()
}

export function formatPrice(price: number | null | undefined): string {
  if (price === null || price === undefined) return '—'
  if (price >= 1000) return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}
