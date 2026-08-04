import { openEventStream, requestFile, requestJson } from '@core/network/apiClient'

export function startAnalysis(repoFullName, language) {
  const query = language ? `?language=${encodeURIComponent(language)}` : ''
  return requestJson(`/analyze/${repoFullName}${query}`, { method: 'POST' })
}

export function openAnalysisStream(analysisId, options) {
  return openEventStream(`/analyze/${analysisId}/stream`, options)
}

export function openDeepenStream(analysisId, options) {
  return openEventStream(`/analyze/${analysisId}/deepen/stream`, options)
}

export function fetchHistory() {
  return requestJson('/analyze/history')
}

export function fetchAnalysis(analysisId) {
  return requestJson(`/analyze/${analysisId}`)
}

export function deleteAnalysis(analysisId) {
  return requestJson(`/analyze/${analysisId}`, { method: 'DELETE' })
}

export function deleteAllAnalyses() {
  return requestJson('/analyze/history/all', { method: 'DELETE' })
}

export function fetchQuota() {
  return requestJson('/analyze/quota')
}

export function downloadReport(analysisId, format) {
  return requestFile(`/analyze/${analysisId}/export/${format}`)
}
