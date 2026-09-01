import { useNavigate, useSearchParams } from 'react-router-dom'
import EmptyState from '@core/components/EmptyState'
import ErrorState from '@core/components/ErrorState'
import PageHeader from '@core/components/PageHeader'
import { Icons } from '@core/design/icons'
import { normalizeLanguage } from '@core/translation'
import useTranslation, { useLanguage } from '@core/translation/useTranslation'
import AnalysisReport from '@features/report/presentation/components/AnalysisReport'
import AnalysisStepper from '../components/AnalysisStepper'
import useQuota from '../provider/useQuota'
import useScanStream, { STREAM_PHASES } from '../provider/useScanStream'
import { hasResults, resultsByAspect } from '../../domain/report'
import { ANALYSIS_STEPS, SCAN_STEPPER } from '../../domain/steps'

function ScanRun({ repoFullName, language }) {
  const t = useTranslation()
  const navigate = useNavigate()
  const { refresh: refreshQuota } = useQuota()

  const {
    phase, currentStep, stepMessages, results, analysisId, analysis,
    error, reconnecting, recoverable, resume,
  } = useScanStream(repoFullName, language, refreshQuota)

  const running = phase === STREAM_PHASES.streaming || phase === STREAM_PHASES.starting

  return (
    <>
      <PageHeader
        icon={<Icons.scan size={22} variant="Linear" />}
        title={t.analysis.scanTitle}
        actions={<span className="page-subject">{repoFullName}</span>}
      />

      {running && (
        <AnalysisStepper
          currentStep={currentStep}
          messages={stepMessages}
          phase={phase}
          steps={SCAN_STEPPER}
        />
      )}

      {reconnecting && (
        <p className="stream-notice">
          <Icons.running size={14} variant="Linear" className="spinning" />
          {t.analysis.reconnecting}
        </p>
      )}

      {phase === STREAM_PHASES.error && (
        <ErrorState message={error} onRetry={recoverable ? resume : undefined} />
      )}

      {phase === STREAM_PHASES.done && (
        <AnalysisReport
          analysis={analysis || { repo_name: repoFullName }}
          results={hasResults(analysis) ? resultsByAspect(analysis) : results}
          pendingSteps={running ? ANALYSIS_STEPS : []}
          action={analysisId && (
            <button className="btn" onClick={() => navigate(`/report/${analysisId}`)}>
              {t.actions.fullReport} <Icons.forward size={14} variant="Linear" />
            </button>
          )}
        />
      )}
    </>
  )
}

function ScanPage() {
  const t = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { language: uiLanguage } = useLanguage()

  const repoFullName = searchParams.get('repo')
  const language = normalizeLanguage(searchParams.get('lang')) || uiLanguage

  if (!repoFullName) {
    return (
      <EmptyState
        icon={<Icons.scan size={30} variant="Linear" />}
        title={t.analysis.scanEmptyTitle}
        text={t.analysis.scanEmptyText}
        action={(
          <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
            {t.actions.goToRepos} <Icons.forward size={14} variant="Linear" />
          </button>
        )}
      />
    )
  }

  return <ScanRun key={`${repoFullName}:${language}`} repoFullName={repoFullName} language={language} />
}

export default ScanPage
