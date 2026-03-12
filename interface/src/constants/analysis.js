import {
  ShieldAlert, FolderGit2, SearchCode, FileText,
  CheckCircle, AlertTriangle, XCircle,
} from 'lucide-react'

export const STEP_ICONS = {
  secrets_detection: ShieldAlert,
  gitignore_check: FolderGit2,
  quality_check: SearchCode,
  readme_check: FileText,
}

export const STEP_LABELS = {
  secrets_detection: 'Detection de secrets',
  gitignore_check: 'Verification .gitignore',
  quality_check: 'Qualite du code',
  readme_check: 'README vs Code',
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

export const ALL_STEPS = ['secrets_detection', 'gitignore_check', 'quality_check', 'readme_check']
