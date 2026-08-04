import { useNavigate } from 'react-router-dom'
import EmptyState from '@core/components/EmptyState'
import ErrorState from '@core/components/ErrorState'
import PageHeader from '@core/components/PageHeader'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import { formatShortDateTime } from '@core/utils/date'
import useAnalysisHistory from '../provider/useAnalysisHistory'
import { isRunning, isViewable, statusConfig } from '../../domain/status'

function HistoryPage() {
  const t = useTranslation()
  const navigate = useNavigate()
  const { analyses, loading, error, actionError, reload, remove, removeAll } = useAnalysisHistory()

  function handleRemoveAll() {
    if (window.confirm(t.analysis.confirmDeleteAll)) removeAll()
  }

  return (
    <>
      <PageHeader
        icon={<Icons.history size={22} variant="Linear" />}
        title={t.analysis.historyTitle}
        count={analyses.length}
        actions={analyses.length > 0 && (
          <button className="btn btn-danger" onClick={handleRemoveAll}>
            <Icons.trash size={14} variant="Linear" /> {t.actions.deleteAll}
          </button>
        )}
      />

      {loading && <Spinner />}

      {!loading && error && (
        <ErrorState message={error || t.errors.historyFailed} onRetry={reload} />
      )}

      {actionError && <ErrorState message={actionError} />}

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
                <div className="history-item-left">
                  <StatusIcon
                    size={18}
                    variant="Linear"
                    style={{ color, flexShrink: 0 }}
                    className={isRunning(analysis) ? 'spinning' : ''}
                  />
                  <div className="history-item-info">
                    <span className="history-repo">{analysis.repo_name}</span>
                    <span className="history-meta">
                      {label} &middot; {formatShortDateTime(analysis.created_at)}
                    </span>
                  </div>
                </div>

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
                    className="btn btn-danger"
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
