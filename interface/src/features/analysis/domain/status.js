import { CheckCircle, Clock, FileSearch, Loader, XCircle } from 'lucide-react'
import { getStrings } from '@core/translation'

export const SCANNED = 'scanned'
export const COMPLETED = 'completed'

const STATUS_CONFIG = {
  scanned: { icon: FileSearch, color: '#2ecc71' },
  completed: { icon: CheckCircle, color: '#2ecc71' },
  scanning: { icon: Loader, color: '#e7a33e' },
  analyzing: { icon: Loader, color: '#e7a33e' },
  processing: { icon: Loader, color: '#e7a33e' },
  pending: { icon: Clock, color: '#888888' },
  failed: { icon: XCircle, color: '#e74c3c' },
}

const VIEWABLE = new Set([SCANNED, COMPLETED])

export function statusConfig(status) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return { ...config, label: getStrings().analysis.statusLabels[status] || status }
}

export function isViewable(analysis) {
  return VIEWABLE.has(analysis?.status)
}

export function canDeepen(analysis) {
  return analysis?.status === SCANNED
}

export function isDeepened(analysis) {
  return analysis?.status === COMPLETED
}
