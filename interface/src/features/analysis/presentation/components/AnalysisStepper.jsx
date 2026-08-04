import { Icons } from '@core/design/icons'
import { SCAN_STEPPER, stepperLabel } from '../../domain/steps'

const STATE_ICONS = {
  active: Icons.running,
  completed: Icons.done,
  error: Icons.error,
}

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

function AnalysisStepper({ currentStep, messages, phase, steps = SCAN_STEPPER }) {
  const activeIndex = steps.findIndex(step => step.key === currentStep)

  return (
    <div className="analysis-stepper">
      {steps.map((step, index) => {
        const state = stateFor(index, activeIndex, phase)
        const StepIcon = STATE_ICONS[state] || step.icon

        return (
          <div key={step.key} style={{ display: 'contents' }}>
            <div className={`stepper-step ${state}`}>
              <div className="stepper-icon">
                <StepIcon
                  size={20}
                  variant="Linear"
                  className={state === 'active' ? 'spinning' : ''}
                />
              </div>
              <span className="stepper-label">{stepperLabel(step.key)}</span>
              {messages[step.key] && <span className="stepper-message">{messages[step.key]}</span>}
            </div>

            {index < steps.length - 1 && (
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
