import { useState } from 'react'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import {
  foldBySeverity,
  groupIssues,
  normalizeIssues,
  normalizeRecommendations,
  splitByVerdict,
} from '@features/scan/domain/issue'
import { RESULT_ICONS, STEP_ICONS, resultColor, resultLabel, stepLabel } from '@features/scan/domain/steps'
import CoverageNote from './CoverageNote'
import FoldedSeverity from './FoldedSeverity'
import IssueRow from './IssueRow'
import MetricsPanel from './MetricsPanel'

function AnalysisResultCard({ aspect, result, pending, coverage }) {
  const t = useTranslation()
  const [showDismissed, setShowDismissed] = useState(false)

  const AspectIcon = STEP_ICONS[aspect] || Icons.clean
  const StatusIcon = RESULT_ICONS[result?.status] || Icons.clean
  const completed = Boolean(result)

  const { retained, dismissed } = splitByVerdict(normalizeIssues(result?.issues))
  const { main, folded } = foldBySeverity(groupIssues(retained))
  const groupedDismissed = groupIssues(dismissed)
  const recommendations = normalizeRecommendations(result?.recommendations)
  const DismissedIcon = showDismissed ? Icons.expand : Icons.collapse

  return (
    <div className={`analysis-result-card ${completed ? result.status : 'pending'}`}>
      <div className="result-card-header">
        <AspectIcon size={20} variant="Linear" />
        <h3>{stepLabel(aspect)}</h3>
        {completed && (
          <span className="result-status" style={{ color: resultColor(result.status) }}>
            <StatusIcon size={16} variant="Linear" />
            {resultLabel(result.status)}
          </span>
        )}
        {!completed && pending && (
          <Icons.running
            size={18}
            variant="Linear"
            className="spinning"
            style={{ marginLeft: 'auto', color: 'var(--ink-faint)' }}
          />
        )}
      </div>

      <div className="result-card-body">
        {!completed && <p className="result-pending">{t.analysis.pending}</p>}

        {completed && result.status === 'partial' && <CoverageNote coverage={coverage} />}

        {completed && result.status === 'unavailable' && (
          <p className="result-clean">{result.message || t.analysis.unavailable}</p>
        )}

        {completed && main.length > 0 && (
          <ul className="issue-list">
            {main.map((issue, index) => (
              <IssueRow key={issue.id || index} issue={issue} />
            ))}
          </ul>
        )}

        {completed && folded.map(group => (
          <FoldedSeverity key={group.severity} group={group} />
        ))}

        {completed && dismissed.length > 0 && (
          <div className="dismissed-section">
            <button
              type="button"
              className="dismissed-toggle"
              onClick={() => setShowDismissed(previous => !previous)}
            >
              <DismissedIcon size={14} variant="Linear" />
              {t.analysis.dismissedTitle.replace('{count}', dismissed.length)}
            </button>
            {showDismissed && (
              <>
                <p className="dismissed-hint">{t.analysis.dismissedHint}</p>
                <ul className="issue-list">
                  {groupedDismissed.map((issue, index) => (
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
