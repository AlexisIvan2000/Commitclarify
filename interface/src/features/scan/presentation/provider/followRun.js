import { ApiError } from '@core/network/errors'
import { getStrings } from '@core/translation'
import { fetchAnalysis } from '../../data/analysisApi'
import { isRunning } from '../../domain/status'
import { TERMINAL_EVENTS } from './streamEvents'

export const RUN_OUTCOMES = {
  done: 'done',
  failed: 'failed',
  lost: 'lost',
  aborted: 'aborted',
}

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000]

const FATAL_STATUSES = new Set([403, 429])

function isFatal(error) {
  return error instanceof ApiError && FATAL_STATUSES.has(error.status)
}

function pause(milliseconds, signal) {
  return new Promise(resolve => {
    const timer = setTimeout(resolve, milliseconds)
    signal.addEventListener('abort', () => {
      clearTimeout(timer)
      resolve()
    }, { once: true })
  })
}

async function currentAnalysis(analysisId, failure) {
  try {
    return await fetchAnalysis(analysisId)
  } catch (caught) {
    throw failure || caught
  }
}

function verdictOf(analysis) {
  if (analysis.status === 'failed') {
    return { event: 'error', message: getStrings().errors.scanFailed }
  }

  return { event: 'done', analysis_id: analysis.id, status: analysis.status }
}

export default async function followRun({ analysisId, openStream, onEvent, signal }) {
  let delivered = 0
  let attempt = 0

  while (!signal.aborted) {
    let terminal = null
    let failure = null
    let received = 0

    try {
      for await (const event of openStream(analysisId, { signal })) {
        if (event.event !== 'ping') received += 1
        onEvent(event)

        if (TERMINAL_EVENTS.has(event.event)) {
          terminal = event.event
          break
        }
      }
    } catch (caught) {
      failure = caught
    }

    if (signal.aborted) return { outcome: RUN_OUTCOMES.aborted }
    if (isFatal(failure)) throw failure

    if (terminal === 'done') {
      return { outcome: RUN_OUTCOMES.done, analysis: await fetchAnalysis(analysisId) }
    }
    if (terminal === 'error') return { outcome: RUN_OUTCOMES.failed }

    const analysis = await currentAnalysis(analysisId, failure)

    if (!isRunning(analysis)) {
      onEvent(verdictOf(analysis))
      const outcome = analysis.status === 'failed' ? RUN_OUTCOMES.failed : RUN_OUTCOMES.done
      return { outcome, analysis }
    }

    if (received > delivered) {
      delivered = received
      attempt = 0
    }

    if (attempt >= RECONNECT_DELAYS.length) return { outcome: RUN_OUTCOMES.lost }

    onEvent({ event: 'reconnecting' })
    await pause(RECONNECT_DELAYS[attempt], signal)
    attempt += 1
  }

  return { outcome: RUN_OUTCOMES.aborted }
}
