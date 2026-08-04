import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import { coverageGaps } from '../../domain/coverage'

function CoverageNote({ coverage }) {
  const t = useTranslation()
  const gaps = coverageGaps(coverage)

  if (gaps.length === 0) return null

  return (
    <div className="coverage-note">
      <Icons.hidden size={15} variant="Linear" />
      <div>
        <p className="coverage-note-lead">{t.analysis.coverage.lead}</p>
        <ul>
          {gaps.map(gap => (
            <li key={gap.key}>
              {gap.count === null
                ? t.analysis.coverage[gap.key]
                : t.analysis.coverage[gap.key].replace('{count}', gap.count.toLocaleString())}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default CoverageNote
