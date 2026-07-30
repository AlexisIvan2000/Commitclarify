import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import ErrorState from '@core/components/ErrorState'
import { normalizeLanguage } from '@core/translation'
import useTranslation, { useLanguage } from '@core/translation/useTranslation'
import AnalysisResultCard from '../components/AnalysisResultCard'
import AnalysisStepper from '../components/AnalysisStepper'
import AppNavbar from '../components/AppNavbar'
import useAnalysisStream, { STREAM_PHASES } from '../provider/useAnalysisStream'
import useQuota from '../provider/useQuota'
import { ANALYSIS_STEPS } from '../../domain/steps'

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
    phase, currentStep, stepMessages, results, analysisId, stats, error,
  } = useAnalysisStream(repoFullName, reportLanguage, refreshQuota)

  return (
    <div className="dash fade-in">
      <AppNavbar />

      <main className="dash-main">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> {t.actions.back}
        </button>

        <div className="analysis-header">
          <h2 className="analysis-title">
            {t.analysis.title} <span className="highlight">{repoFullName}</span>
          </h2>
          <span className={`analysis-phase ${phase}`}>{t.analysis.phases[phase]}</span>
        </div>

        <AnalysisStepper currentStep={currentStep} messages={stepMessages} phase={phase} />

        {stats && (
          <div className="progress-stats-bar">
            <span>{stats.fetched} {t.analysis.files}</span>
            <span>{stats.skipped} {t.analysis.skipped}</span>
          </div>
        )}

        <div className="analysis-results-grid">
          {ANALYSIS_STEPS.map(step => (
            <AnalysisResultCard
              key={step}
              aspect={step}
              result={results[step]}
              pending={phase === STREAM_PHASES.streaming}
            />
          ))}
        </div>

        {phase === STREAM_PHASES.error && <ErrorState message={error} />}

        {phase === STREAM_PHASES.done && analysisId && (
          <div className="analysis-done-actions">
            <button
              className="repo-action-btn primary"
              onClick={() => navigate(`/analysis/${analysisId}`)}
            >
              {t.actions.fullReport}
            </button>
            <button className="repo-action-btn" onClick={() => navigate('/history')}>
              {t.actions.history}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default AnalysisStreamPage
