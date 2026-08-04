import { useCallback, useEffect, useRef, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { fetchAnalysis, openDeepenStream } from '../../data/analysisApi'
import {
  STREAM_PHASES,
  TERMINAL_EVENTS,
  emptyStreamState,
  reduceEvent,
} from './streamEvents'

export { STREAM_PHASES }

export default function useDeepenStream(analysisId, onFinished) {
  const [state, setState] = useState(() => emptyStreamState(STREAM_PHASES.idle))

  const running = useRef(false)
  const mounted = useRef(true)
  const finishedCallback = useRef(onFinished)
  finishedCallback.current = onFinished

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const start = useCallback(async () => {
    if (running.current || !analysisId) return
    running.current = true

    setState(emptyStreamState(STREAM_PHASES.streaming))

    try {
      let finished = false

      for await (const event of openDeepenStream(analysisId)) {
        if (mounted.current) setState(previous => reduceEvent(previous, event))
        if (TERMINAL_EVENTS.has(event.event)) {
          finished = event.event === 'done'
          break
        }
      }

      if (finished && mounted.current) {
        finishedCallback.current?.(await fetchAnalysis(analysisId))
      }
    } catch (caught) {
      if (mounted.current) {
        setState(previous => ({
          ...previous,
          phase: STREAM_PHASES.error,
          error: messageOf(caught),
        }))
      }
    } finally {
      running.current = false
    }
  }, [analysisId])

  return { ...state, start }
}
