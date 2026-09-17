// Single source of truth for agent icon/display-name/state-label lookups —
// previously copy-pasted with the same four entries in AgentCard, AgentStatusPill,
// AgentDetailView, and DashboardView.
import { useI18n } from 'vue-i18n'

const ICONS: Record<string, string> = {
  auto_trend: '📈',
  xrp_swing: '🌊',
  p2p_market: '🤝',
  manual: '👁️',
}

const NAMES: Record<string, string> = {
  auto_trend: 'Auto Trend',
  xrp_swing: 'XRP Swing',
  p2p_market: 'P2P Market',
  manual: 'Manual',
}

export function agentIcon(agentType: string): string {
  return ICONS[agentType] || '🤖'
}

export function agentDisplayName(agentType: string): string {
  return NAMES[agentType] || agentType
}

export function useAgentMeta() {
  const { t } = useI18n()

  function stateLabel(state: string | undefined): string {
    const labels: Record<string, string> = {
      running: t('agents.running'),
      paused: t('agents.paused'),
      stopped: t('agents.stopped'),
      error: t('agents.error'),
      starting: t('agents.starting'),
      stopping: t('agents.stopping'),
    }
    return (state && labels[state]) || state || t('agents.stopped')
  }

  return { agentIcon, agentDisplayName, stateLabel }
}
