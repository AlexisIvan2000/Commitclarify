import { useCallback, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ErrorState from '@core/components/ErrorState'
import PageHeader from '@core/components/PageHeader'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import { CATALOGS } from '@core/translation'
import useTranslation from '@core/translation/useTranslation'
import AnalysisReport from '../components/AnalysisReport'
import AnalysisStepper from '@features/scan/presentation/components/AnalysisStepper'
import DeepenAction from '../components/DeepenAction'
import useAnalysisDetail from '../provider/useAnalysisDetail'
import useDeepenStream, { STREAM_PHASES } from '../provider/useDeepenStream'
import useQuota from '@features/scan/presentation/provider/useQuota'
import useReportExport from '../provider/useReportExport'
import { resultsByAspect } from '@features/scan/domain/report'
import { canDeepen } from '@features/scan/domain/status'
import { DEEPEN_STEPPER } from '@features/scan/domain/steps'

function ReportPage() {
  const t = useTranslation()
  const { analysisId } = useParams()
  const navigate = useNavigate()
  const { analysis, loading, error, reload } = useAnalysisDetail(analysisId)
  const { exportReport, pendingFormat, error: exportError } = useReportExport(analysisId)
  const { quota, refresh: refreshQuota } = useQuota()
  const [deepened, setDeepened] = useState(null)

  const onDeepened = useCallback((updated) => {
    setDeepened(updated)
    refreshQuota?.()
  }, [refreshQuota])

  const deepen = useDeepenStream(analysisId, onDeepened)
  const shown = deepened || analysis
  const deepening = deepen.phase === STREAM_PHASES.streaming

  return (
    <>
      <PageHeader
        icon={<Icons.report size={22} variant="Linear" />}
        title={t.analysis.reportTitle}
        actions={(
          <button className="btn btn-quiet" onClick={() => navigate('/history')}>
            <Icons.history size={14} variant="Linear" /> {t.actions.history}
          </button>
        )}
      />

      {loading && <Spinner />}

      {!loading && error && (
        <ErrorState message={error || t.errors.analysisNotFound} onRetry={reload} />
      )}

      {!loading && !error && shown && (
        <>
          <div className="export-actions">
            <button
              className="btn"
              onClick={() => exportReport('pdf')}
              disabled={pendingFormat !== null}
            >
              <Icons.exportPdf size={14} variant="Linear" /> {t.actions.exportPdf}
            </button>
            <button
              className="btn"
              onClick={() => exportReport('json')}
              disabled={pendingFormat !== null}
            >
              <Icons.exportJson size={14} variant="Linear" /> {t.actions.exportJson}
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

          {deepen.reconnecting && (
            <p className="stream-notice">
              <Icons.running size={14} variant="Linear" className="spinning" />
              {t.analysis.reconnecting}
            </p>
          )}

          {deepen.phase === STREAM_PHASES.error && (
            <ErrorState
              message={deepen.error}
              onRetry={deepen.recoverable ? deepen.start : undefined}
            />
          )}

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
    </>
  )
}

export default ReportPage
