import { getStrings } from '@core/translation'
import { Icons } from '@core/design/icons'

export const SCANNED = 'scanned'
export const COMPLETED = 'completed'

const STATUS_CONFIG = {
  scanned: { icon: Icons.scanned, color: 'var(--link)' },
  completed: { icon: Icons.completed, color: 'var(--ok-fg)' },
  scanning: { icon: Icons.scanning, color: 'var(--sev-high-fg)' },
  analyzing: { icon: Icons.analyzing, color: 'var(--sev-high-fg)' },
  processing: { icon: Icons.processing, color: 'var(--sev-high-fg)' },
  pending: { icon: Icons.pending, color: 'var(--ink-faint)' },
  failed: { icon: Icons.failed, color: 'var(--sev-critical-fg)' },
}

const VIEWABLE = new Set([SCANNED, COMPLETED])
const RUNNING = new Set(['pending', 'scanning', 'analyzing', 'processing'])

export function statusConfig(status) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return { ...config, label: getStrings().analysis.statusLabels[status] || status }
}

export function isViewable(analysis) {
  return VIEWABLE.has(analysis?.status)
}

export function isRunning(analysis) {
  return RUNNING.has(analysis?.status)
}

export function canDeepen(analysis) {
  return analysis?.status === SCANNED
}

export function isDeepened(analysis) {
  return analysis?.status === COMPLETED
}
