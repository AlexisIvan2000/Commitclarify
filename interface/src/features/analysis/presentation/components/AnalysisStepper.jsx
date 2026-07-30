import { CheckCircle, Loader, XCircle } from 'lucide-react'
import { STEPPER_STEPS, stepperLabel } from '../../domain/steps'

function stateFor(index, activeIndex, phase) {
  if (phase === 'error') {
    if (index === activeIndex) return 'error'
    return index < activeIndex ? 'completed' : 'pending'
  }
  if (phase === 'done') return 'completed'
  if (index < activeIndex) return 'completed'
  if (index === activeIndex) return 'active'
  return 'pending'
}

function StateIcon({ state, fallback }) {
  const Fallback = fallback

  if (state === 'active') return <Loader size={20} className="spinning" />
  if (state === 'completed') return <CheckCircle size={20} />
  if (state === 'error') return <XCircle size={20} />
  return <Fallback size={20} />
}

function AnalysisStepper({ currentStep, messages, phase }) {
  const activeIndex = STEPPER_STEPS.findIndex(step => step.key === currentStep)

  return (
    <div className="analysis-stepper">
      {STEPPER_STEPS.map((step, index) => {
        const state = stateFor(index, activeIndex, phase)

        return (
          <div key={step.key} style={{ display: 'contents' }}>
            <div className={`stepper-step ${state}`}>
              <div className="stepper-icon">
                <StateIcon state={state} fallback={step.icon} />
              </div>
              <span className="stepper-label">{stepperLabel(step.key)}</span>
              {messages[step.key] && <span className="stepper-message">{messages[step.key]}</span>}
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
