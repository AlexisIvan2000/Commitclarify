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
    reconnecting: false,
    recoverable: false,
    error: null,
  }
}

export function reduceEvent(state, event) {
  switch (event.event) {
    case 'progress':
      if (!event.step) return state
      return {
        ...state,
        reconnecting: false,
        currentStep: event.step,
        stepMessages: { ...state.stepMessages, [event.step]: event.message },
      }
    case 'step_complete':
      return {
        ...state,
        reconnecting: false,
        results: { ...state.results, [event.step]: event.result },
      }
    case 'done':
      return { ...state, reconnecting: false, currentStep: 'done', phase: STREAM_PHASES.done }
    case 'error':
      return { ...state, reconnecting: false, phase: STREAM_PHASES.error, error: event.message }
    case 'reconnecting':
      return { ...state, reconnecting: true }
    case 'ping':
      return state.reconnecting ? { ...state, reconnecting: false } : state
    default:
      return state
  }
}
