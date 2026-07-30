import {
  ShieldAlert, FolderGit2, SearchCode, FileText,
  CheckCircle, AlertTriangle, XCircle,
  Download, Database, Brain,
} from 'lucide-react'
import { getStrings } from '@core/translation'

export const ANALYSIS_STEPS = ['secrets_detection', 'gitignore_check', 'quality_check', 'readme_check']

export const STEP_ICONS = {
  secrets_detection: ShieldAlert,
  gitignore_check: FolderGit2,
  quality_check: SearchCode,
  readme_check: FileText,
}

export const STATUS_ICONS = {
  clean: CheckCircle,
  warning: AlertTriangle,
  alert: XCircle,
}

export const STATUS_COLORS = {
  clean: '#2ecc71',
  warning: '#e7a33e',
  alert: '#e74c3c',
}

export const STEPPER_STEPS = [
  { key: 'fetching', icon: Download },
  { key: 'indexing', icon: Database },
  { key: 'analyzing', icon: Brain },
  { key: 'done', icon: CheckCircle },
]

export function stepLabel(step) {
  return getStrings().analysis.stepLabels[step] || step
}

export function stepperLabel(step) {
  return getStrings().analysis.stepperLabels[step] || step
}

export function statusColor(status) {
  return STATUS_COLORS[status] || '#888888'
}
