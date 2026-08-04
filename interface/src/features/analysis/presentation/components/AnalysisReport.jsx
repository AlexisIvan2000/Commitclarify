import { GitCommit } from 'lucide-react'
import useTranslation from '@core/translation/useTranslation'
import { formatDateTime } from '@core/utils/date'
import { analyzedFiles, shortSha } from '../../domain/coverage'
import { ANALYSIS_STEPS } from '../../domain/steps'
import AnalysisResultCard from './AnalysisResultCard'

function AnalysisReport({ analysis, results, pendingSteps = [], action = null }) {
  const t = useTranslation()
  const coverage = analysis?.coverage || null
  const sha = shortSha(coverage, analysis)
  const files = analyzedFiles(coverage)

  return (
    <div className="analysis-report">
      <header className="report-header">
        <div>
          <h2>{analysis?.repo_name}</h2>
          <p className="report-provenance">
            <GitCommit size={14} />
            {analysis?.completed_at && formatDateTime(analysis.completed_at)}
            {sha && <code>{sha}</code>}
            {files && (
              <span>
                {t.analysis.filesRead
                  .replace('{read}', files.read.toLocaleString())
                  .replace('{tracked}', files.tracked.toLocaleString())}
              </span>
            )}
          </p>
        </div>
        {action}
      </header>

      <div className="report-axes">
        {ANALYSIS_STEPS.map(aspect => (
          <AnalysisResultCard
            key={aspect}
            aspect={aspect}
            result={results[aspect]}
            pending={pendingSteps.includes(aspect)}
            coverage={coverage}
          />
        ))}
      </div>
    </div>
  )
}

export default AnalysisReport
