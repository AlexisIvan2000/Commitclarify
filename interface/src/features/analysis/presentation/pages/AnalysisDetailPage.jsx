import { useCallback, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileDown, FileJson } from 'lucide-react'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import { CATALOGS } from '@core/translation'
import useTranslation from '@core/translation/useTranslation'
import AnalysisReport from '../components/AnalysisReport'
import AnalysisStepper from '../components/AnalysisStepper'
import AppNavbar from '../components/AppNavbar'
import DeepenAction from '../components/DeepenAction'
import useAnalysisDetail from '../provider/useAnalysisDetail'
import useDeepenStream, { STREAM_PHASES } from '../provider/useDeepenStream'
import useQuota from '../provider/useQuota'
import useReportExport from '../provider/useReportExport'
import { resultsByAspect } from '../../domain/report'
import { canDeepen } from '../../domain/status'
import { DEEPEN_STEPPER } from '../../domain/steps'

function AnalysisDetailPage() {
  const t = useTranslation()
  const { analysisId } = useParams()
  const navigate = useNavigate()
  const { analysis, loading, error, reload } = useAnalysisDetail(analysisId)
  const { exportReport, pendingFormat, error: exportError } = useReportExport(analysisId)
  const { quota, refresh: refreshQuota } = useQuota()
  const [deepened, setDeepened] = useState(null)

  const onDeepened = useCallback(updated => {
    setDeepened(updated)
    refreshQuota?.()
  }, [refreshQuota])

  const deepen = useDeepenStream(analysisId, onDeepened)
  const shown = deepened || analysis
  const deepening = deepen.phase === STREAM_PHASES.streaming

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

        {!loading && !error && shown && (
          <>
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
              {CATALOGS[shown.language] && (
                <span className="report-language-badge">
                  {t.analysis.generatedIn} {CATALOGS[shown.language].languageName}
                </span>
              )}
            </div>

            {exportError && <ErrorState message={exportError} />}

            {deepening && (
              <AnalysisStepper
                currentStep={deepen.currentStep}
                messages={deepen.stepMessages}
                phase={deepen.phase}
                steps={DEEPEN_STEPPER}
              />
            )}

            {deepen.phase === STREAM_PHASES.error && <ErrorState message={deepen.error} />}

            <AnalysisReport
              analysis={shown}
              results={resultsByAspect(shown)}
              action={canDeepen(shown) && (
                <DeepenAction
                  remaining={quota?.remaining}
                  running={deepening}
                  onStart={deepen.start}
                />
              )}
            />
          </>
        )}
      </main>
    </div>
  )
}

export default AnalysisDetailPage
