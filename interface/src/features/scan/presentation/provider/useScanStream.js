import { useCallback, useEffect, useRef, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { getStrings } from '@core/translation'
import { openAnalysisStream, startAnalysis } from '../../data/analysisApi'
import followRun, { RUN_OUTCOMES } from './followRun'
import { STREAM_PHASES, emptyStreamState, reduceEvent } from './streamEvents'

export { STREAM_PHASES }

export default function useScanStream(repoFullName, language, onStarted) {
  const [state, setState] = useState(() => emptyStreamState())
  const [analysisId, setAnalysisId] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [attach, setAttach] = useState(0)

  const requested = useRef(false)
  const startedCallback = useRef(onStarted)

  useEffect(() => {
    startedCallback.current = onStarted
  }, [onStarted])

  useEffect(() => {
    if (!repoFullName || requested.current) return undefined
    requested.current = true

    let abandoned = false

    startAnalysis(repoFullName, language)
      .then(({ analysis_id: created }) => {
        if (abandoned) return
        startedCallback.current?.()
        setAnalysisId(created)
        setState(previous => ({ ...previous, phase: STREAM_PHASES.streaming }))
      })
      .catch(caught => {
        if (abandoned) return
        setState(previous => ({
          ...previous,
          phase: STREAM_PHASES.error,
          error: messageOf(caught),
        }))
      })

    return () => { abandoned = true }
  }, [repoFullName, language])

  useEffect(() => {
    if (!analysisId) return undefined

    const controller = new AbortController()

    followRun({
      analysisId,
      openStream: openAnalysisStream,
      onEvent: event => setState(previous => reduceEvent(previous, event)),
      signal: controller.signal,
    })
      .then(({ outcome, analysis: loaded }) => {
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

        if (loaded) setAnalysis(loaded)
      })
      .catch(caught => {
        if (controller.signal.aborted) return
        setState(previous => ({
          ...previous,
          reconnecting: false,
          phase: STREAM_PHASES.error,
          error: messageOf(caught),
        }))
      })

    return () => controller.abort()
  }, [analysisId, attach])

  const resume = useCallback(() => {
    setState(emptyStreamState(STREAM_PHASES.streaming))
    setAttach(previous => previous + 1)
  }, [])

  return { ...state, analysisId, analysis, resume }
}
