export function isComplete(coverage) {
  if (!coverage) return true
  return coverage.complete !== false
}

function sumValues(record) {
  if (!record || typeof record !== 'object') return 0
  return Object.values(record).reduce((total, count) => total + (Number(count) || 0), 0)
}

export function coverageGaps(coverage) {
  if (!coverage || isComplete(coverage)) return []

  const gaps = []

  if (coverage.capped_over_limit > 0) {
    gaps.push({ key: 'capped', count: coverage.capped_over_limit })
  }
  if (coverage.tree_truncated) {
    gaps.push({ key: 'truncated', count: null })
  }

  const failures = sumValues(coverage.fetch_failures)
  if (failures > 0) {
    gaps.push({ key: 'failures', count: failures })
  }

  return gaps
}

export function analyzedFiles(coverage) {
  if (!coverage) return null

  return {
    read: coverage.fetched_files ?? null,
    tracked: coverage.tracked_files ?? null,
  }
}

export function shortSha(coverage, analysis) {
  const sha = coverage?.sha || analysis?.repo_sha
  return typeof sha === 'string' ? sha.slice(0, 7) : null
}
