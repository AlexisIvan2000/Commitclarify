import { Download, Database, Brain, CheckCircle, Loader, XCircle } from 'lucide-react'

const STEPPER_STEPS = [
  { key: 'fetching', label: 'Recuperation', icon: Download },
  { key: 'indexing', label: 'Indexation', icon: Database },
  { key: 'analyzing', label: 'Analyse IA', icon: Brain },
  { key: 'done', label: 'Termine', icon: CheckCircle },
]

function AnalysisStepper({ currentStep, messages, phase }) {
  const stepIndex = STEPPER_STEPS.findIndex(s => s.key === currentStep)

  function getStepState(index) {
    if (phase === 'error') {
      if (index === stepIndex) return 'error'
      if (index < stepIndex) return 'completed'
      return 'pending'
    }
    if (phase === 'done') return 'completed'
    if (index < stepIndex) return 'completed'
    if (index === stepIndex) return 'active'
    return 'pending'
  }

  return (
    <div className="analysis-stepper">
      {STEPPER_STEPS.map((step, index) => {
        const state = getStepState(index)
        const Icon = step.icon
        const message = messages[step.key]

        return (
          <div key={step.key} style={{ display: 'contents' }}>
            <div className={`stepper-step ${state}`}>
              <div className="stepper-icon">
                {state === 'active' ? (
                  <Loader size={20} className="spinning" />
                ) : state === 'completed' ? (
                  <CheckCircle size={20} />
                ) : state === 'error' ? (
                  <XCircle size={20} />
                ) : (
                  <Icon size={20} />
                )}
              </div>
              <span className="stepper-label">{step.label}</span>
              {message && <span className="stepper-message">{message}</span>}
            </div>
            {index < STEPPER_STEPS.length - 1 && (
              <div className={`stepper-connector ${state === 'completed' ? 'filled' : ''}`}>
                <div className="stepper-connector-fill" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default AnalysisStepper
