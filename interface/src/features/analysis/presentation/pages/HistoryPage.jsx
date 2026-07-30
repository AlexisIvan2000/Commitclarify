import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Eye, History as HistoryIcon, Trash2 } from 'lucide-react'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import useTranslation from '@core/translation/useTranslation'
import { formatShortDateTime } from '@core/utils/date'
import AppNavbar from '../components/AppNavbar'
import useAnalysisHistory from '../provider/useAnalysisHistory'
import { isViewable, statusConfig } from '../../domain/status'

function HistoryPage() {
  const t = useTranslation()
  const navigate = useNavigate()
  const { analyses, loading, error, actionError, reload, remove, removeAll } = useAnalysisHistory()

  function handleRemoveAll() {
    if (window.confirm(t.analysis.confirmDeleteAll)) removeAll()
  }

  return (
    <div className="dash fade-in">
      <AppNavbar />

      <main className="dash-main">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> {t.actions.back}
        </button>

        <div className="dash-section-header">
          <h2 className="dash-section-title">
            <HistoryIcon size={22} />
            {t.analysis.historyTitle} ({analyses.length})
          </h2>
          {analyses.length > 0 && (
            <button className="repo-action-btn danger" onClick={handleRemoveAll}>
              <Trash2 size={14} /> {t.actions.deleteAll}
            </button>
          )}
        </div>

        {loading && <Spinner />}

        {!loading && error && (
          <ErrorState message={error || t.errors.historyFailed} onRetry={reload} />
        )}

        {actionError && <ErrorState message={actionError} />}

        {!loading && !error && analyses.length === 0 && (
          <p className="no-results">{t.analysis.historyEmpty}</p>
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
                      style={{ color, flexShrink: 0 }}
                      className={analysis.status === 'processing' ? 'spinning' : ''}
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
                        className="repo-action-btn"
                        onClick={() => navigate(`/analysis/${analysis.id}`)}
                      >
                        <Eye size={14} /> {t.actions.view}
                      </button>
                    )}
                    <button
                      className="repo-action-btn danger"
                      onClick={() => remove(analysis.id)}
                      aria-label={`${t.actions.deleteAnalysisOf} ${analysis.repo_name}`}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}

export default HistoryPage
