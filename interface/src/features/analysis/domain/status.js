import { CheckCircle, Clock, Loader, XCircle } from 'lucide-react'
import { getStrings } from '@core/translation'

const STATUS_CONFIG = {
  completed: { icon: CheckCircle, color: '#2ecc71' },
  processing: { icon: Loader, color: '#e7a33e' },
  pending: { icon: Clock, color: '#888888' },
  failed: { icon: XCircle, color: '#e74c3c' },
}

export function statusConfig(status) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return { ...config, label: getStrings().analysis.statusLabels[status] || status }
}

export function isViewable(analysis) {
  return analysis?.status === 'completed'
}
