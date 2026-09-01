import { getStrings } from '@core/translation'

export const FALSE_POSITIVE = 'false_positive'
export const UNCERTAIN = 'uncertain'
export const CONFIRMED = 'confirmed'

export const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info']

export const SEVERITY_COLORS = {
  critical: 'var(--sev-critical-fg)',
  high: 'var(--sev-high-fg)',
  medium: 'var(--sev-medium-fg)',
  low: 'var(--sev-low-fg)',
  info: 'var(--sev-info-fg)',
}

function firstText(...candidates) {
  return candidates.find(value => typeof value === 'string' && value.trim()) || null
}

function lineNumbers(issue) {
  if (!Array.isArray(issue.locations)) return []
  return issue.locations.map(location => location?.line).filter(Number.isInteger)
}

export function normalizeIssue(issue) {
  if (typeof issue === 'string') {
    return { title: issue, filePath: null, codeHint: null, severity: null, lines: [] }
  }
  if (!issue || typeof issue !== 'object') return null

  return {
    id: firstText(issue.id),
    title: firstText(issue.title, issue.message, issue.description)
      || getStrings().analysis.untitledIssue,
    description: firstText(issue.description),
    filePath: firstText(issue.file_path),
    codeHint: firstText(issue.code_hint),
    rule: firstText(issue.rule),
    source: firstText(issue.source),
    severity: firstText(issue.severity),
    originalSeverity: firstText(issue.original_severity),
    verdict: firstText(issue.verdict),
    verdictReason: firstText(issue.verdict_reason),
    isTestFile: issue.context === 'test',
    occurrences: Number.isInteger(issue.occurrences) ? issue.occurrences : 1,
    lines: lineNumbers(issue),
  }
}

export function normalizeRecommendation(recommendation) {
  if (typeof recommendation === 'string') return { text: recommendation, priority: null }
  if (!recommendation || typeof recommendation !== 'object') return null

  return {
    text: firstText(recommendation.message, recommendation.description, recommendation.title)
      || getStrings().analysis.untitledRecommendation,
    priority: firstText(recommendation.priority),
  }
}

export function normalizeIssues(issues) {
  return Array.isArray(issues) ? issues.map(normalizeIssue).filter(Boolean) : []
}

export function normalizeRecommendations(recommendations) {
  return Array.isArray(recommendations)
    ? recommendations.map(normalizeRecommendation).filter(Boolean)
    : []
}

export function severityRank(severity) {
  const rank = SEVERITY_ORDER.indexOf(severity)
  return rank === -1 ? SEVERITY_ORDER.length : rank
}

export function severityColor(severity) {
  return SEVERITY_COLORS[severity] || SEVERITY_COLORS.low
}

export function isDismissed(issue) {
  return issue.verdict === FALSE_POSITIVE
}

export function splitByVerdict(issues) {
  const sorted = [...issues].sort((a, b) => severityRank(a.severity) - severityRank(b.severity))

  return {
    retained: sorted.filter(issue => !isDismissed(issue)),
    dismissed: sorted.filter(isDismissed),
  }
}

export function verdictLabel(verdict) {
  return getStrings().analysis.verdictLabels[verdict] || null
}

export const MAIN_SEVERITIES = new Set(['critical', 'high', 'medium'])
export const FOLDED_SEVERITIES = ['low', 'info']

const GROUP_SEPARATOR = '␟'

function groupKey(issue) {
  return `${issue.rule || issue.title}${GROUP_SEPARATOR}${issue.filePath || ''}`
}

export function groupIssues(issues) {
  const groups = new Map()

  for (const issue of issues) {
    const key = groupKey(issue)
    const existing = groups.get(key)

    if (!existing) {
      groups.set(key, { ...issue, entries: 1, occurrences: issue.occurrences, lines: [...issue.lines] })
      continue
    }

    existing.entries += 1
    existing.occurrences += issue.occurrences
    existing.lines = [...existing.lines, ...issue.lines]
  }

  return [...groups.values()].sort(
    (a, b) => severityRank(a.severity) - severityRank(b.severity),
  )
}

export function foldBySeverity(entries) {
  const main = entries.filter(entry => MAIN_SEVERITIES.has(entry.severity))

  const folded = FOLDED_SEVERITIES
    .map(severity => ({
      severity,
      entries: entries.filter(entry => entry.severity === severity),
    }))
    .filter(group => group.entries.length > 0)
    .map(group => ({
      ...group,
      detections: group.entries.reduce((total, entry) => total + entry.occurrences, 0),
    }))

  return { main, folded }
}
