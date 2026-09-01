import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import EmptyState from '@core/components/EmptyState'
import ErrorState from '@core/components/ErrorState'
import PageHeader from '@core/components/PageHeader'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import { formatShortDateTime } from '@core/utils/date'
import useAnalysisHistory from '../provider/useAnalysisHistory'
import { isRunning, isViewable, statusConfig } from '@features/scan/domain/status'

function HistoryPage() {
  const t = useTranslation()
  const navigate = useNavigate()
  const { analyses, loading, error, actionError, reload, remove, removeAll } = useAnalysisHistory()

  const [confirming, setConfirming] = useState(false)

  return (
    <>
      <PageHeader
        icon={<Icons.history size={22} variant="Linear" />}
        title={t.analysis.historyTitle}
        count={analyses.length}
        actions={analyses.length > 0 && !confirming && (
          <button className="btn btn-quiet" onClick={() => setConfirming(true)}>
            <Icons.trash size={14} variant="Linear" /> {t.actions.deleteAll}
          </button>
        )}
      />

      {loading && <Spinner />}

      {!loading && error && (
        <ErrorState message={error || t.errors.historyFailed} onRetry={reload} />
      )}

      {actionError && <ErrorState message={actionError} />}

      {confirming && (
        <div className="confirm-banner" role="alertdialog" aria-label={t.analysis.confirmDeleteAllTitle}>
          <Icons.critical size={17} variant="Linear" />
          <div className="confirm-text">
            <strong>{t.analysis.confirmDeleteAllTitle.replace('{count}', analyses.length)}</strong>
            <span>{t.analysis.confirmDeleteAllText}</span>
          </div>
          <button
            className="btn btn-danger"
            onClick={() => { setConfirming(false); removeAll() }}
          >
            <Icons.trash size={13} variant="Linear" /> {t.actions.deleteAll}
          </button>
          <button className="btn" onClick={() => setConfirming(false)}>{t.actions.cancel}</button>
        </div>
      )}

      {!loading && !error && analyses.length === 0 && (
        <EmptyState
          icon={<Icons.history size={30} variant="Linear" />}
          title={t.analysis.historyEmpty}
          action={(
            <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
              {t.actions.goToRepos} <Icons.forward size={14} variant="Linear" />
            </button>
          )}
        />
      )}

      {!loading && !error && analyses.length > 0 && (
        <div className="history-list">
          {analyses.map((analysis) => {
            const { icon: StatusIcon, color, label } = statusConfig(analysis.status)

            return (
              <div key={analysis.id} className="history-item">
                <span className="history-repo">{analysis.repo_name}</span>

                <span className={`history-status ${analysis.status}`} style={{ color }}>
                  <StatusIcon
                    size={13}
                    variant="Linear"
                    className={isRunning(analysis) ? 'spinning' : ''}
                  />
                  {label}
                </span>

                <span className="history-date">{formatShortDateTime(analysis.created_at)}</span>

                <div className="history-item-actions">
                  {isViewable(analysis) && (
                    <button
                      className="btn"
                      onClick={() => navigate(`/report/${analysis.id}`)}
                    >
                      <Icons.view size={14} variant="Linear" /> {t.actions.view}
                    </button>
                  )}
                  <button
                    className="btn btn-quiet history-remove"
                    onClick={() => remove(analysis.id)}
                    aria-label={`${t.actions.deleteAnalysisOf} ${analysis.repo_name}`}
                  >
                    <Icons.trash size={14} variant="Linear" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}

export default HistoryPage
