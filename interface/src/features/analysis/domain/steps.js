import { getStrings } from '@core/translation'
import { Icons } from '@core/design/icons'

export const ANALYSIS_STEPS = ['secrets_detection', 'gitignore_check', 'quality_check', 'readme_check']

export const STEP_ICONS = {
  secrets_detection: Icons.secrets_detection,
  gitignore_check: Icons.gitignore_check,
  quality_check: Icons.quality_check,
  readme_check: Icons.readme_check,
}

export const RESULT_ICONS = {
  clean: Icons.clean,
  partial: Icons.partial,
  issues_found: Icons.issues_found,
  unavailable: Icons.unavailable,
  error: Icons.error,
}

export const RESULT_COLORS = {
  clean: 'var(--ok-fg)',
  partial: 'var(--ink-soft)',
  issues_found: 'var(--sev-high-fg)',
  unavailable: 'var(--ink-faint)',
  error: 'var(--sev-critical-fg)',
}

export const SCAN_STEPPER = [
  { key: 'fetching', icon: Icons.fetching },
  { key: 'scanning', icon: Icons.scan },
  { key: 'done', icon: Icons.done },
]

export const DEEPEN_STEPPER = [
  { key: 'fetching', icon: Icons.fetching },
  { key: 'indexing', icon: Icons.indexing },
  { key: 'analyzing', icon: Icons.aiAnalyzing },
  { key: 'done', icon: Icons.done },
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
  return RESULT_COLORS[status] || 'var(--ink-faint)'
}
