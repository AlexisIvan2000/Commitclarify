import { useEffect } from 'react'
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
import useRuns from '../provider/useRuns'
import { STREAM_PHASES } from '../provider/streamEvents'
import { SCAN } from '../../domain/runs'
import { hasResults, resultsByAspect } from '../../domain/report'
import { ANALYSIS_STEPS, SCAN_STEPPER } from '../../domain/steps'

function ScanPage() {
  const t = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { language: uiLanguage } = useLanguage()
  const { refresh: refreshQuota } = useQuota()
  const { run, startScan, release } = useRuns()

  const repoFullName = searchParams.get('repo')
  const language = normalizeLanguage(searchParams.get('lang')) || uiLanguage

  const live = Boolean(run && run.phase === STREAM_PHASES.streaming)
  const mine = Boolean(run && run.kind === SCAN && run.repoFullName === repoFullName)
  const elsewhere = live && !mine

  useEffect(() => {
    if (!repoFullName || mine || live) return
    startScan(repoFullName, language).then(() => refreshQuota?.())
  }, [repoFullName, language, mine, live, startScan, refreshQuota])

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

  const running = mine && run.phase === STREAM_PHASES.streaming
  const done = mine && run.phase === STREAM_PHASES.done

  return (
    <>
      <PageHeader
        icon={<Icons.scan size={22} variant="Linear" />}
        title={t.analysis.scanTitle}
        actions={<span className="page-subject">{repoFullName}</span>}
      />

      {elsewhere && (
        <EmptyState
          icon={<Icons.running size={30} variant="Linear" className="spinning" />}
          title={t.runs.busyTitle}
          text={t.runs.busyText.replace('{repo}', run.repoFullName)}
          action={(
            <button className="btn" onClick={() => navigate(`/scan?repo=${run.repoFullName}`)}>
              {t.runs.followIt} <Icons.forward size={14} variant="Linear" />
            </button>
          )}
        />
      )}

      {running && (
        <AnalysisStepper
          currentStep={run.currentStep}
          messages={run.stepMessages}
          phase={run.phase}
          steps={SCAN_STEPPER}
        />
      )}

      {mine && run.reconnecting && (
        <p className="stream-notice">
          <Icons.running size={14} variant="Linear" className="spinning" />
          {t.analysis.reconnecting}
        </p>
      )}

      {running && run.slow && (
        <p className="stream-notice patience">
          <Icons.pending size={14} variant="Linear" />
          {t.runs.takingLonger}
        </p>
      )}

      {mine && run.phase === STREAM_PHASES.error && (
        <ErrorState
          message={run.error}
          onRetry={() => {
            release()
            startScan(repoFullName, language)
          }}
        />
      )}

      {done && (
        <AnalysisReport
          analysis={run.analysis || { repo_name: repoFullName }}
          results={hasResults(run.analysis) ? resultsByAspect(run.analysis) : run.results}
          pendingSteps={running ? ANALYSIS_STEPS : []}
          action={run.analysisId && (
            <button className="btn" onClick={() => navigate(`/report/${run.analysisId}`)}>
              {t.actions.fullReport} <Icons.forward size={14} variant="Linear" />
            </button>
          )}
        />
      )}
    </>
  )
}

export default ScanPage
