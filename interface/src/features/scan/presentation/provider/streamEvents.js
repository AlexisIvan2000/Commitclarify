export const STREAM_PHASES = {
  idle: 'idle',
  starting: 'starting',
  streaming: 'streaming',
  done: 'done',
  error: 'error',
}

export const TERMINAL_EVENTS = new Set(['done', 'error'])

export function emptyStreamState(phase = STREAM_PHASES.starting) {
  return {
    phase,
    currentStep: 'fetching',
    stepMessages: {},
    results: {},
    error: null,
  }
}

export function reduceEvent(state, event) {
  switch (event.event) {
    case 'progress':
      if (!event.step) return state
      return {
        ...state,
        currentStep: event.step,
        stepMessages: { ...state.stepMessages, [event.step]: event.message },
      }
    case 'step_complete':
      return { ...state, results: { ...state.results, [event.step]: event.result } }
    case 'done':
      return { ...state, currentStep: 'done', phase: STREAM_PHASES.done }
    case 'error':
      return { ...state, phase: STREAM_PHASES.error, error: event.message }
    default:
      return state
  }
}
