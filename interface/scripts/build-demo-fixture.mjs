import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const SOURCE = join(here, '..', '..', 'server', 'scan_react.json')
const TARGET = join(here, '..', 'src', 'features', 'report', 'demo', 'reactScan.json')

const AXES = ['secrets_detection', 'gitignore_check', 'quality_check', 'readme_check']
const MAX_EVIDENCE = 160
const MAX_LOCATIONS = 8

const DISMISSED = {
  'no-unused-vars': "Fichiers de fixture end-to-end du dépôt React : ces variables existent pour le cas de test, elles ne sont pas du code mort.",
}

const CONFIRMED = {
  'gitignore.unprotected': "Le fichier est bien suivi par Git. Même dans un répertoire de fixtures, un .env versionné finit dans l'historique public du dépôt.",
}

function toIssue(finding) {
  const locations = (finding.locations || []).slice(0, MAX_LOCATIONS)

  return {
    id: finding.id,
    severity: finding.severity,
    title: finding.title,
    rule: finding.rule,
    file_path: finding.file_path || 'N/A',
    description: finding.description,
    code_hint: finding.evidence ? finding.evidence.slice(0, MAX_EVIDENCE) : '',
    source: finding.source,
    context: finding.context,
    occurrences: finding.occurrences,
    locations: locations.map(({ line }) => ({ line })),
  }
}

function triage(issue) {
  if (CONFIRMED[issue.rule]) {
    return { ...issue, verdict: 'confirmed', verdict_reason: CONFIRMED[issue.rule] }
  }

  if (DISMISSED[issue.rule] && issue.file_path.includes('__tests__')) {
    return {
      ...issue,
      severity: 'info',
      original_severity: issue.severity,
      verdict: 'false_positive',
      verdict_reason: DISMISSED[issue.rule],
    }
  }

  return issue
}

const scan = JSON.parse(readFileSync(SOURCE, 'utf8'))

const results = AXES.map((aspect) => {
  const axis = scan.axes[aspect]
  return {
    aspect,
    status: axis.status,
    issues: axis.findings.map(toIssue),
    recommendations: [],
    metrics: axis.metrics && Object.keys(axis.metrics).length ? axis.metrics : null,
  }
})

const base = {
  repo_name: 'facebook/react',
  repo_sha: scan.coverage.sha,
  status: 'scanned',
  language: scan.language,
  created_at: '2026-08-03T09:11:00Z',
  completed_at: '2026-08-03T09:12:41Z',
  coverage: { ...scan.coverage, complete: scan.complete },
  results,
}

const sorted = {
  ...base,
  status: 'completed',
  results: results.map(result => ({
    ...result,
    issues: result.issues.map(triage),
  })),
}

const payload = { base, sorted }
writeFileSync(TARGET, JSON.stringify(payload), 'utf8')

const size = JSON.stringify(payload).length
const findings = results.reduce((total, r) => total + r.issues.length, 0)
const dismissed = sorted.results.reduce(
  (total, r) => total + r.issues.filter(i => i.verdict === 'false_positive').length, 0,
)
console.log(`fixture ecrite : ${findings} detections, ${dismissed} ecartees par l'IA, ${(size / 1024).toFixed(1)} Ko`)
