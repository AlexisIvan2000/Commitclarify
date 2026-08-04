import { useState } from 'react'
import { CheckCircle, ChevronDown, ChevronRight, Loader } from 'lucide-react'
import useTranslation from '@core/translation/useTranslation'
import { normalizeIssues, normalizeRecommendations, splitByVerdict } from '../../domain/issue'
import { RESULT_ICONS, STEP_ICONS, resultColor, resultLabel, stepLabel } from '../../domain/steps'
import CoverageNote from './CoverageNote'
import IssueRow from './IssueRow'
import MetricsPanel from './MetricsPanel'

function AnalysisResultCard({ aspect, result, pending, coverage }) {
  const t = useTranslation()
  const [showDismissed, setShowDismissed] = useState(false)

  const Icon = STEP_ICONS[aspect] || CheckCircle
  const StatusIcon = RESULT_ICONS[result?.status] || CheckCircle
  const completed = Boolean(result)

  const { retained, dismissed } = splitByVerdict(normalizeIssues(result?.issues))
  const recommendations = normalizeRecommendations(result?.recommendations)
  const DismissedIcon = showDismissed ? ChevronDown : ChevronRight

  return (
    <div className={`analysis-result-card ${completed ? result.status : 'pending'}`}>
      <div className="result-card-header">
        <Icon size={20} />
        <h3>{stepLabel(aspect)}</h3>
        {completed && (
          <span className="result-status" style={{ color: resultColor(result.status) }}>
            <StatusIcon size={16} />
            {resultLabel(result.status)}
          </span>
        )}
        {!completed && pending && (
          <Loader size={18} className="spinning" style={{ marginLeft: 'auto', color: '#888888' }} />
        )}
      </div>

      <div className="result-card-body">
        {!completed && <p className="result-pending">{t.analysis.pending}</p>}

        {completed && result.status === 'partial' && <CoverageNote coverage={coverage} />}

        {completed && result.status === 'unavailable' && (
          <p className="result-clean">{result.message || t.analysis.unavailable}</p>
        )}

        {completed && retained.length > 0 && (
          <ul className="issue-list">
            {retained.map((issue, index) => (
              <IssueRow key={issue.id || index} issue={issue} />
            ))}
          </ul>
        )}

        {completed && dismissed.length > 0 && (
          <div className="dismissed-section">
            <button
              type="button"
              className="dismissed-toggle"
              onClick={() => setShowDismissed(previous => !previous)}
            >
              <DismissedIcon size={14} />
              {t.analysis.dismissedTitle.replace('{count}', dismissed.length)}
            </button>
            {showDismissed && (
              <>
                <p className="dismissed-hint">{t.analysis.dismissedHint}</p>
                <ul className="issue-list">
                  {dismissed.map((issue, index) => (
                    <IssueRow key={issue.id || index} issue={issue} />
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        {completed && aspect === 'quality_check' && <MetricsPanel metrics={result.metrics} />}

        {completed && recommendations.length > 0 && (
          <div className="result-section">
            <h4>{t.analysis.recommendations}</h4>
            <ul>
              {recommendations.map((recommendation, index) => (
                <li key={index} className="result-rec">{recommendation.text}</li>
              ))}
            </ul>
          </div>
        )}

        {completed && result.status === 'clean' && (
          <p className="result-clean">{t.analysis.clean}</p>
        )}
      </div>
    </div>
  )
}

export default AnalysisResultCard
