import useTranslation from '@core/translation/useTranslation'

function present(value) {
  return value !== null && value !== undefined
}

function MetricsPanel({ metrics }) {
  const t = useTranslation()

  if (!metrics) return null

  const complexity = metrics.complexity || {}
  const missing = metrics.missing_lockfiles || []

  const rows = [
    {
      key: 'tests',
      value: metrics.has_tests ? t.analysis.metrics.present : t.analysis.metrics.absent,
    },
    {
      key: 'ci',
      value: metrics.has_ci ? t.analysis.metrics.present : t.analysis.metrics.absent,
    },
    {
      key: 'lockfile',
      value: missing.length === 0
        ? t.analysis.metrics.present
        : t.analysis.metrics.missingFor.replace('{ecosystems}', missing.join(', ')),
    },
    {
      key: 'complexity',
      value: present(complexity.max)
        ? t.analysis.metrics.complexityValue
          .replace('{max}', complexity.max)
          .replace('{over}', complexity.over_threshold ?? 0)
          .replace('{threshold}', complexity.threshold)
        : t.analysis.metrics.notMeasured,
    },
    {
      key: 'sample',
      value: t.analysis.metrics.sampleValue
        .replace('{source}', metrics.source_files_in_sample ?? 0)
        .replace('{tests}', metrics.test_files_in_sample ?? 0),
    },
  ]

  return (
    <div className="metrics-panel">
      <h4>{t.analysis.metrics.title}</h4>
      <dl>
        {rows.map(row => (
          <div key={row.key} className="metrics-row">
            <dt>{t.analysis.metrics.labels[row.key]}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
      {complexity.unanalyzed_languages?.length > 0 && (
        <p className="metrics-caveat">
          {t.analysis.metrics.unanalyzed.replace(
            '{languages}',
            complexity.unanalyzed_languages.join(', '),
          )}
        </p>
      )}
    </div>
  )
}

export default MetricsPanel
