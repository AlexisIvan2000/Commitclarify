import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import { chunkCoverage } from '@features/scan/domain/coverage'

function ChunkCoverageNote({ coverage }) {
  const t = useTranslation()
  const chunks = chunkCoverage(coverage)

  if (!chunks) return null

  const labels = t.analysis.chunkCoverage
  const named = chunks.tiers
    .map(({ tier, count }) => `${labels.tiers[tier] || tier} (${count.toLocaleString()})`)
    .join(', ')

  return (
    <div className="coverage-note">
      <Icons.indexing size={15} variant="Linear" />
      <div>
        <p className="coverage-note-lead">
          {labels.lead
            .replace('{indexed}', chunks.indexed.toLocaleString())
            .replace('{total}', chunks.total.toLocaleString())}
        </p>
        <ul>
          <li>{labels.breakdown.replace('{detail}', named)}</li>
          {chunks.involuntary > 0 && (
            <li>{labels.involuntary.replace('{count}', chunks.involuntary.toLocaleString())}</li>
          )}
        </ul>
      </div>
    </div>
  )
}

export default ChunkCoverageNote
