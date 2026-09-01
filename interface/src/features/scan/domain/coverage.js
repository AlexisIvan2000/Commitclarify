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
  const read = coverage?.fetched_files
  const tracked = coverage?.tracked_files

  if (!Number.isInteger(read) || !Number.isInteger(tracked)) return null

  return { read, tracked }
}

export function shortSha(coverage, analysis) {
  const sha = coverage?.sha || analysis?.repo_sha
  return typeof sha === 'string' ? sha.slice(0, 7) : null
}

const DELIBERATE_TIERS = new Set(['genere_ou_vendored', 'tests'])

export function chunkCoverage(coverage) {
  const chunks = coverage?.chunks

  if (!chunks || chunks.complete !== false || !(chunks.dropped > 0)) return null

  const byTier = chunks.dropped_by_tier || {}
  const deliberate = Object.entries(byTier)
    .filter(([tier]) => DELIBERATE_TIERS.has(tier))
    .reduce((total, [, count]) => total + count, 0)

  return {
    total: chunks.total,
    indexed: chunks.indexed,
    dropped: chunks.dropped,
    deliberate,
    involuntary: chunks.dropped - deliberate,
    tiers: Object.entries(byTier)
      .map(([tier, count]) => ({ tier, count }))
      .sort((a, b) => b.count - a.count),
  }
}
