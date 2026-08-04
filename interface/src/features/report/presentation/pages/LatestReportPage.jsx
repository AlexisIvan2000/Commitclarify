import { Navigate, useNavigate } from 'react-router-dom'
import EmptyState from '@core/components/EmptyState'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import useAnalysisHistory from '@features/history/presentation/provider/useAnalysisHistory'
import { isViewable } from '@features/scan/domain/status'

function LatestReportPage() {
  const t = useTranslation()
  const navigate = useNavigate()
  const { analyses, loading, error, reload } = useAnalysisHistory()

  if (loading) return <Spinner />
  if (error) return <ErrorState message={error || t.errors.historyFailed} onRetry={reload} />

  const latest = analyses.find(isViewable)
  if (latest) return <Navigate to={`/report/${latest.id}`} replace />

  return (
    <EmptyState
      icon={<Icons.report size={30} variant="Linear" />}
      title={t.analysis.reportEmptyTitle}
      text={t.analysis.reportEmptyText}
      action={(
        <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
          {t.actions.goToRepos} <Icons.forward size={14} variant="Linear" />
        </button>
      )}
    />
  )
}

export default LatestReportPage
