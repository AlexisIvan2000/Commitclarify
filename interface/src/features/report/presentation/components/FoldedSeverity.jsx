import { useState } from 'react'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import { severityColor } from '@features/scan/domain/issue'
import IssueRow from './IssueRow'

function FoldedSeverity({ group }) {
  const t = useTranslation()
  const [open, setOpen] = useState(false)

  const ChevronIcon = open ? Icons.expand : Icons.collapse
  const label = t.analysis.severityLabels[group.severity] || group.severity
  const entries = group.entries.length

  const counts = entries === group.detections
    ? t.analysis.folded.replace('{count}', group.detections)
    : t.analysis.foldedGrouped
      .replace('{detections}', group.detections)
      .replace('{entries}', entries)

  return (
    <div className="folded-severity">
      <button
        type="button"
        className="folded-toggle"
        onClick={() => setOpen(previous => !previous)}
        aria-expanded={open}
      >
        <span className="folded-label">
          <span
            className="issue-severity"
            style={{ backgroundColor: severityColor(group.severity) }}
          />
          {label}
        </span>
        <span className="folded-counts">{counts}</span>
        <ChevronIcon size={14} variant="Linear" />
      </button>

      {open && (
        <ul className="issue-list">
          {group.entries.map((issue, index) => (
            <IssueRow key={issue.id || index} issue={issue} />
          ))}
        </ul>
      )}
    </div>
  )
}

export default FoldedSeverity
