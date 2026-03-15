import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CheckCircle, Loader, ArrowLeft, XCircle } from 'lucide-react'
import { startAnalysis, streamAnalysis, getToken } from '../services/api'
import { STEP_ICONS, STEP_LABELS, STATUS_ICONS, STATUS_COLORS, ALL_STEPS } from '../constants/analysis'
import Navbar from '../components/Navbar'
import AnalysisStepper from '../components/AnalysisStepper'
import CodeHighlight from '../components/CodeHighlight'

function AnalysisStream({ user, onLogout }) {
  const { owner, repo } = useParams()
  const navigate = useNavigate()
  const repoFullName = `${owner}/${repo}`

  const [phase, setPhase] = useState('starting')
  const [currentStep, setCurrentStep] = useState('fetching')
  const [stepMessages, setStepMessages] = useState({})
  const [results, setResults] = useState({})
  const [analysisId, setAnalysisId] = useState(null)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const started = useRef(false)

  useEffect(() => {
    if (!getToken()) {
      navigate('/')
      return
    }
    if (started.current) return
    started.current = true

    async function run() {
      try {
        const { analysis_id } = await startAnalysis(repoFullName)
        setAnalysisId(analysis_id)
        setPhase('streaming')

        const stream = streamAnalysis(analysis_id)
        for await (const event of stream) {
          handleSSEEvent(event)
        }
      } catch (err) {
        setError(err.message || 'Une erreur est survenue')
        setPhase('error')
      }
    }

    run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleSSEEvent(event) {
    switch (event.event) {
      case 'progress':
        if (event.step) {
          setCurrentStep(event.step)
          setStepMessages(prev => ({ ...prev, [event.step]: event.message }))
        }
        if (event.stats) {
          setStats(event.stats)
        }
        break
      case 'step_complete':
        setResults(prev => ({ ...prev, [event.step]: event.result }))
        break
      case 'done':
        setCurrentStep('done')
        setPhase('done')
        break
      case 'error':
        setError(event.message)
        setPhase('error')
        break
    }
  }

  return (
    <div className="dash fade-in">
      <Navbar user={user} onLogout={onLogout} />

      <main className="dash-main">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Retour
        </button>

        <div className="analysis-header">
          <h2 className="analysis-title">Analyse de <span className="highlight">{repoFullName}</span></h2>
          <span className={`analysis-phase ${phase}`}>
            {phase === 'starting' && 'Demarrage...'}
            {phase === 'streaming' && 'Analyse en cours...'}
            {phase === 'done' && 'Terminee'}
            {phase === 'error' && 'Erreur'}
          </span>
        </div>

        <AnalysisStepper
          currentStep={currentStep}
          messages={stepMessages}
          phase={phase}
        />

        {stats && (
          <div className="progress-stats-bar">
            <span>{stats.fetched} fichiers</span>
            <span>{stats.skipped} ignores</span>
          </div>
        )}

        <div className="analysis-results-grid">
          {ALL_STEPS.map(step => {
            const Icon = STEP_ICONS[step]
            const result = results[step]
            const isCompleted = !!result
            const isPending = !isCompleted && phase === 'streaming'

            return (
              <div key={step} className={`analysis-result-card ${isCompleted ? result.status : 'pending'}`}>
                <div className="result-card-header">
                  <Icon size={20} />
                  <h3>{STEP_LABELS[step]}</h3>
                  {isCompleted ? (
                    (() => {
                      const StatusIcon = STATUS_ICONS[result.status] || CheckCircle
                      const color = STATUS_COLORS[result.status] || '#888'
                      return <StatusIcon size={18} style={{ color, marginLeft: 'auto' }} />
                    })()
                  ) : isPending ? (
                    <Loader size={18} className="spinning" style={{ marginLeft: 'auto', color: '#888' }} />
                  ) : null}
                </div>

                {isCompleted ? (
                  <div className="result-card-body">
                    {result.issues && result.issues.length > 0 && (
                      <div className="result-section">
                        <h4>Problemes ({result.issues.length})</h4>
                        <ul>
                          {result.issues.map((issue, i) => (
                            <li key={i} className="result-issue">
                              {typeof issue === 'string' ? issue : (
                                <>
                                  <span>{issue.title || issue.message || issue.description || JSON.stringify(issue)}</span>
                                  {issue.file_path && <span className="issue-file">{issue.file_path}</span>}
                                  {issue.code_hint && (
                                    <CodeHighlight code={issue.code_hint} filePath={issue.file_path} />
                                  )}
                                </>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {result.recommendations && result.recommendations.length > 0 && (
                      <div className="result-section">
                        <h4>Recommandations</h4>
                        <ul>
                          {result.recommendations.map((rec, i) => (
                            <li key={i} className="result-rec">{typeof rec === 'string' ? rec : rec.message || rec.description || JSON.stringify(rec)}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {(!result.issues || result.issues.length === 0) && (!result.recommendations || result.recommendations.length === 0) && (
                      <p className="result-clean">Aucun probleme detecte.</p>
                    )}
                  </div>
                ) : (
                  <div className="result-card-body">
                    <p className="result-pending">En attente...</p>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {phase === 'error' && (
          <div className="analysis-error">
            <XCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {phase === 'done' && analysisId && (
          <div className="analysis-done-actions">
            <button className="repo-action-btn primary" onClick={() => navigate(`/analysis/${analysisId}`)}>
              Voir le rapport complet
            </button>
            <button className="repo-action-btn" onClick={() => navigate('/history')}>
              Historique
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default AnalysisStream
