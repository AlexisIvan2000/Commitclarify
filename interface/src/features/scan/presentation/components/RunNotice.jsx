import { useNavigate } from 'react-router-dom'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import useRuns from '../provider/useRuns'

function RunNotice() {
  const t = useTranslation()
  const navigate = useNavigate()
  const { notice, dismissNotice } = useRuns()

  if (!notice) return null

  const failed = notice.tone === 'error'
  const NoticeIcon = failed ? Icons.error : Icons.clean

  return (
    <div className={`run-notice ${notice.tone}`} role="status" aria-live="polite">
      <NoticeIcon size={16} variant="Linear" />

      <div className="run-notice-text">
        <span className="run-notice-message">{notice.message}</span>
        {notice.repoFullName && (
          <span className="run-notice-repo">{notice.repoFullName}</span>
        )}
      </div>

      {!failed && notice.analysisId && (
        <button
          type="button"
          className="run-notice-link"
          onClick={() => {
            dismissNotice()
            navigate(`/report/${notice.analysisId}`)
          }}
        >
          {t.runs.openReport}
        </button>
      )}

      <button
        type="button"
        className="run-notice-close"
        onClick={dismissNotice}
        title={t.actions.dismiss}
        aria-label={t.actions.dismiss}
      >
        <Icons.error size={14} variant="Linear" />
      </button>
    </div>
  )
}

export default RunNotice
