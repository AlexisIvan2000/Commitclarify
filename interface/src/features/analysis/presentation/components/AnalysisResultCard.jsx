import { CheckCircle, Loader } from 'lucide-react'
import CodeHighlight from '@core/components/CodeHighlight'
import useTranslation from '@core/translation/useTranslation'
import { normalizeIssues, normalizeRecommendations } from '../../domain/issue'
import { STATUS_ICONS, STEP_ICONS, statusColor, stepLabel } from '../../domain/steps'

function AnalysisResultCard({ aspect, result, pending }) {
  const t = useTranslation()
  const Icon = STEP_ICONS[aspect] || CheckCircle
  const StatusIcon = STATUS_ICONS[result?.status] || CheckCircle
  const completed = Boolean(result)
  const issues = normalizeIssues(result?.issues)
  const recommendations = normalizeRecommendations(result?.recommendations)

  return (
    <div className={`analysis-result-card ${completed ? result.status : 'pending'}`}>
      <div className="result-card-header">
        <Icon size={20} />
        <h3>{stepLabel(aspect)}</h3>
        {completed && (
          <StatusIcon size={18} style={{ color: statusColor(result.status), marginLeft: 'auto' }} />
        )}
        {!completed && pending && (
          <Loader size={18} className="spinning" style={{ marginLeft: 'auto', color: '#888888' }} />
        )}
      </div>

      <div className="result-card-body">
        {!completed && <p className="result-pending">{t.analysis.pending}</p>}

        {completed && issues.length > 0 && (
          <div className="result-section">
            <h4>{t.analysis.issues} ({issues.length})</h4>
            <ul>
              {issues.map((issue, index) => (
                <li key={index} className="result-issue">
                  <span>{issue.title}</span>
                  {issue.filePath && <span className="issue-file">{issue.filePath}</span>}
                  {issue.codeHint && <CodeHighlight code={issue.codeHint} filePath={issue.filePath} />}
                </li>
              ))}
            </ul>
          </div>
        )}

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

        {completed && issues.length === 0 && recommendations.length === 0 && (
          <p className="result-clean">{t.analysis.clean}</p>
        )}
      </div>
    </div>
  )
}

export default AnalysisResultCard
