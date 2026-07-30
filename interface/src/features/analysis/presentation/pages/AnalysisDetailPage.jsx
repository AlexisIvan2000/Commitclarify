import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileDown, FileJson } from 'lucide-react'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import { CATALOGS } from '@core/translation'
import useTranslation from '@core/translation/useTranslation'
import { formatDateTime } from '@core/utils/date'
import AnalysisResultCard from '../components/AnalysisResultCard'
import AppNavbar from '../components/AppNavbar'
import useAnalysisDetail from '../provider/useAnalysisDetail'
import useReportExport from '../provider/useReportExport'

function AnalysisDetailPage() {
  const t = useTranslation()
  const { analysisId } = useParams()
  const navigate = useNavigate()
  const { analysis, loading, error, reload } = useAnalysisDetail(analysisId)
  const { exportReport, pendingFormat, error: exportError } = useReportExport(analysisId)

  const results = Array.isArray(analysis?.results) ? analysis.results : []

  return (
    <div className="dash fade-in">
      <AppNavbar />

      <main className="dash-main">
        <button className="back-btn" onClick={() => navigate('/history')}>
          <ArrowLeft size={16} /> {t.actions.back}
        </button>

        {loading && <Spinner />}

        {!loading && error && (
          <ErrorState message={error || t.errors.analysisNotFound} onRetry={reload} />
        )}

        {!loading && !error && analysis && (
          <>
            <div className="analysis-header">
              <h2 className="analysis-title">
                {t.analysis.reportTitle} <span className="highlight">{analysis.repo_name}</span>
              </h2>
              <span className="analysis-date">{formatDateTime(analysis.created_at)}</span>
              {CATALOGS[analysis.language] && (
                <span className="report-language-badge">
                  {t.analysis.generatedIn} {CATALOGS[analysis.language].languageName}
                </span>
              )}
            </div>

            <div className="export-actions">
              <button
                className="repo-action-btn"
                onClick={() => exportReport('pdf')}
                disabled={pendingFormat !== null}
              >
                <FileDown size={14} /> {t.actions.exportPdf}
              </button>
              <button
                className="repo-action-btn"
                onClick={() => exportReport('json')}
                disabled={pendingFormat !== null}
              >
                <FileJson size={14} /> {t.actions.exportJson}
              </button>
            </div>

            {exportError && <ErrorState message={exportError} />}

            {results.length === 0 ? (
              <p className="no-results">{t.analysis.emptyResults}</p>
            ) : (
              <div className="analysis-results-grid">
                {results.map(result => (
                  <AnalysisResultCard key={result.id} aspect={result.aspect} result={result} />
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default AnalysisDetailPage
