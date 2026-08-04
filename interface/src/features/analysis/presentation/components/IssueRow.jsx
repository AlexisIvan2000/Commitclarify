import { FlaskConical } from 'lucide-react'
import CodeHighlight from '@core/components/CodeHighlight'
import useTranslation from '@core/translation/useTranslation'
import { severityColor, verdictLabel } from '../../domain/issue'

function IssueRow({ issue }) {
  const t = useTranslation()
  const location = issue.lines.length > 0
    ? `${issue.filePath}:${issue.lines.join(', ')}`
    : issue.filePath

  return (
    <li className="issue-row">
      <div className="issue-row-head">
        <span
          className="issue-severity"
          style={{ backgroundColor: severityColor(issue.severity) }}
          title={t.analysis.severityLabels[issue.severity] || issue.severity}
        />
        <span className="issue-title">{issue.title}</span>

        {issue.isTestFile && (
          <span className="issue-badge test">
            <FlaskConical size={12} />
            {t.analysis.testFile}
          </span>
        )}

        {issue.occurrences > 1 && (
          <span className="issue-badge">
            {t.analysis.occurrences.replace('{count}', issue.occurrences)}
          </span>
        )}
      </div>

      {location && <span className="issue-file">{location}</span>}

      {issue.description && <p className="issue-description">{issue.description}</p>}

      {issue.codeHint && <CodeHighlight code={issue.codeHint} filePath={issue.filePath} />}

      {issue.verdict && (
        <p className="issue-verdict">
          <strong>{verdictLabel(issue.verdict)}</strong>
          {issue.originalSeverity && (
            <span className="issue-demoted">
              {t.analysis.demotedFrom.replace(
                '{severity}',
                t.analysis.severityLabels[issue.originalSeverity] || issue.originalSeverity,
              )}
            </span>
          )}
          {issue.verdictReason && <span> — {issue.verdictReason}</span>}
        </p>
      )}
    </li>
  )
}

export default IssueRow
