import { COMPLETED, SCANNED } from '@features/scan/domain/status'

export const NEVER = 'never'
export const CLEAN = 'clean'
export const SCANNED_STATE = 'scanned'
export const RUNNING = 'running'
export const FAILED = 'failed'

const VIEWABLE = new Set([SCANNED, COMPLETED])
const IN_FLIGHT = new Set(['pending', 'scanning', 'analyzing', 'processing'])

export function lastScanByRepo(analyses) {
  const latest = new Map()

  for (const analysis of analyses) {
    const known = latest.get(analysis.repo_name)
    if (!known || new Date(analysis.created_at) > new Date(known.created_at)) {
      latest.set(analysis.repo_name, analysis)
    }
  }

  return latest
}

export function scanState(analysis) {
  if (!analysis) return { state: NEVER, analysis: null }
  if (IN_FLIGHT.has(analysis.status)) return { state: RUNNING, analysis }
  if (analysis.status === 'failed') return { state: FAILED, analysis }
  if (VIEWABLE.has(analysis.status)) return { state: SCANNED_STATE, analysis }

  return { state: NEVER, analysis: null }
}
