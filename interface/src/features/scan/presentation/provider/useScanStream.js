import { useEffect, useRef, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { fetchAnalysis, openAnalysisStream, startAnalysis } from '../../data/analysisApi'
import {
  STREAM_PHASES,
  TERMINAL_EVENTS,
  emptyStreamState,
  reduceEvent,
} from './streamEvents'

export { STREAM_PHASES }

export default function useScanStream(repoFullName, language, onStarted) {
  const [state, setState] = useState(() => emptyStreamState())
  const [analysisId, setAnalysisId] = useState(null)
  const [analysis, setAnalysis] = useState(null)

  const started = useRef(false)
  const mounted = useRef(true)
  const startedCallback = useRef(onStarted)
  startedCallback.current = onStarted

  useEffect(() => {
    mounted.current = true

    async function run() {
      try {
        const { analysis_id: newAnalysisId } = await startAnalysis(repoFullName, language)
        startedCallback.current?.()

        if (mounted.current) {
          setAnalysisId(newAnalysisId)
          setState(previous => ({ ...previous, phase: STREAM_PHASES.streaming }))
        }

        let finished = false

        for await (const event of openAnalysisStream(newAnalysisId)) {
          if (mounted.current) setState(previous => reduceEvent(previous, event))
          if (TERMINAL_EVENTS.has(event.event)) {
            finished = event.event === 'done'
            break
          }
        }

        if (finished && mounted.current) {
          setAnalysis(await fetchAnalysis(newAnalysisId))
        }
      } catch (caught) {
        if (!mounted.current) return
        setState(previous => ({
          ...previous,
          phase: STREAM_PHASES.error,
          error: messageOf(caught),
        }))
      }
    }

    if (!started.current && repoFullName) {
      started.current = true
      run()
    }

    return () => { mounted.current = false }
  }, [repoFullName, language])

  return { ...state, analysisId, analysis }
}
