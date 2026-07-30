import { getStrings } from '@core/translation'

function firstText(...candidates) {
  return candidates.find(value => typeof value === 'string' && value.trim()) || null
}

export function normalizeIssue(issue) {
  if (typeof issue === 'string') {
    return { title: issue, filePath: null, codeHint: null, severity: null }
  }
  if (!issue || typeof issue !== 'object') return null

  return {
    title: firstText(issue.title, issue.message, issue.description)
      || getStrings().analysis.untitledIssue,
    filePath: firstText(issue.file_path),
    codeHint: firstText(issue.code_hint),
    severity: firstText(issue.severity),
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
