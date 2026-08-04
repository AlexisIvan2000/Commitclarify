import {
  ShieldAlert, FolderGit2, SearchCode, FileText,
  CheckCircle, AlertTriangle, XCircle, EyeOff, HelpCircle,
  Download, Database, Brain, ScanSearch,
} from 'lucide-react'
import { getStrings } from '@core/translation'

export const ANALYSIS_STEPS = ['secrets_detection', 'gitignore_check', 'quality_check', 'readme_check']

export const STEP_ICONS = {
  secrets_detection: ShieldAlert,
  gitignore_check: FolderGit2,
  quality_check: SearchCode,
  readme_check: FileText,
}

export const RESULT_ICONS = {
  clean: CheckCircle,
  partial: HelpCircle,
  issues_found: AlertTriangle,
  unavailable: EyeOff,
  error: XCircle,
}

export const RESULT_COLORS = {
  clean: '#2ecc71',
  partial: '#7f8c8d',
  issues_found: '#e7a33e',
  unavailable: '#888888',
  error: '#e74c3c',
}

export const SCAN_STEPPER = [
  { key: 'fetching', icon: Download },
  { key: 'scanning', icon: ScanSearch },
  { key: 'done', icon: CheckCircle },
]

export const DEEPEN_STEPPER = [
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

export function resultLabel(status) {
  return getStrings().analysis.resultLabels[status] || status
}

export function resultColor(status) {
  return RESULT_COLORS[status] || '#888888'
}
