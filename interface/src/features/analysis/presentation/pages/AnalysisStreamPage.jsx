import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import ErrorState from '@core/components/ErrorState'
import { normalizeLanguage } from '@core/translation'
import useTranslation, { useLanguage } from '@core/translation/useTranslation'
import AnalysisReport from '../components/AnalysisReport'
import AnalysisStepper from '../components/AnalysisStepper'
import AppNavbar from '../components/AppNavbar'
import useQuota from '../provider/useQuota'
import useScanStream, { STREAM_PHASES } from '../provider/useScanStream'
import { ANALYSIS_STEPS, SCAN_STEPPER } from '../../domain/steps'

function AnalysisStreamPage() {
  const t = useTranslation()
  const { owner, repo } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { language: uiLanguage } = useLanguage()
  const { refresh: refreshQuota } = useQuota()
  const repoFullName = `${owner}/${repo}`
  const reportLanguage = normalizeLanguage(searchParams.get('lang')) || uiLanguage

  const {
    phase, currentStep, stepMessages, results, analysisId, analysis, error,
  } = useScanStream(repoFullName, reportLanguage, refreshQuota)

  const running = phase === STREAM_PHASES.streaming || phase === STREAM_PHASES.starting
  const pendingSteps = running ? ANALYSIS_STEPS : []

  return (
    <div className="dash fade-in">
      <AppNavbar />

      <main className="dash-main">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> {t.actions.back}
        </button>

        {running && (
          <>
            <div className="analysis-header">
              <h2 className="analysis-title">
                {t.analysis.title} <span className="highlight">{repoFullName}</span>
              </h2>
            </div>
            <AnalysisStepper
              currentStep={currentStep}
              messages={stepMessages}
              phase={phase}
              steps={SCAN_STEPPER}
            />
          </>
        )}

        {phase === STREAM_PHASES.error && <ErrorState message={error} />}

        {phase === STREAM_PHASES.done && (
          <AnalysisReport
            analysis={analysis || { repo_name: repoFullName }}
            results={results}
            pendingSteps={pendingSteps}
            action={
              <button
                className="repo-action-btn"
                onClick={() => navigate(`/analysis/${analysisId}`)}
              >
                {t.actions.fullReport}
              </button>
            }
          />
        )}
      </main>
    </div>
  )
}

export default AnalysisStreamPage
