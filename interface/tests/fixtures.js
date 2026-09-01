import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { CATALOGS } from '@core/translation'

export function loadScan(name) {
  return JSON.parse(readFileSync(join(process.cwd(), '..', 'server', `${name}.json`), 'utf8'))
}

export function issuesOf(axisResult) {
  return axisResult.findings.map(finding => ({ ...finding, code_hint: finding.evidence }))
}

export function resultOf(axisResult) {
  return {
    status: axisResult.status,
    issues: issuesOf(axisResult),
    recommendations: [],
    metrics: axisResult.metrics,
  }
}

export const french = {
  language: 'fr',
  strings: CATALOGS.fr,
  available: ['fr', 'en'],
  changeLanguage: () => {},
}
