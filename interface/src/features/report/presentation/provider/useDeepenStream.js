import { useCallback, useEffect, useRef, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { getStrings } from '@core/translation'
import { openDeepenStream } from '@features/scan/data/analysisApi'
import followRun, { RUN_OUTCOMES } from '@features/scan/presentation/provider/followRun'
import {
  STREAM_PHASES,
  emptyStreamState,
  reduceEvent,
} from '@features/scan/presentation/provider/streamEvents'

export { STREAM_PHASES }

export default function useDeepenStream(analysisId, onFinished) {
  const [state, setState] = useState(() => emptyStreamState(STREAM_PHASES.idle))

  const running = useRef(false)
  const connection = useRef(null)
  const finishedCallback = useRef(onFinished)

  useEffect(() => {
    finishedCallback.current = onFinished
  }, [onFinished])

  useEffect(() => () => connection.current?.abort(), [])

  const start = useCallback(async () => {
    if (running.current || !analysisId) return
    running.current = true

    const controller = new AbortController()
    connection.current = controller

    setState(emptyStreamState(STREAM_PHASES.streaming))

    try {
      const { outcome, analysis } = await followRun({
        analysisId,
        openStream: openDeepenStream,
        onEvent: event => setState(previous => reduceEvent(previous, event)),
        signal: controller.signal,
      })

      if (controller.signal.aborted) return

      if (outcome === RUN_OUTCOMES.lost) {
        setState(previous => ({
          ...previous,
          reconnecting: false,
          recoverable: true,
          phase: STREAM_PHASES.error,
          error: getStrings().errors.streamLost,
        }))
        return
      }

      if (outcome === RUN_OUTCOMES.done && analysis) finishedCallback.current?.(analysis)
    } catch (caught) {
      if (controller.signal.aborted) return
      setState(previous => ({
        ...previous,
        reconnecting: false,
        phase: STREAM_PHASES.error,
        error: messageOf(caught),
      }))
    } finally {
      running.current = false
    }
  }, [analysisId])

  return { ...state, start }
}
