import { useEffect, useRef, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { openAnalysisStream, startAnalysis } from '../../data/analysisApi'

export const STREAM_PHASES = {
  starting: 'starting',
  streaming: 'streaming',
  done: 'done',
  error: 'error',
}

export default function useAnalysisStream(repoFullName, language, onStarted) {
  const [phase, setPhase] = useState(STREAM_PHASES.starting)
  const [currentStep, setCurrentStep] = useState('fetching')
  const [stepMessages, setStepMessages] = useState({})
  const [results, setResults] = useState({})
  const [analysisId, setAnalysisId] = useState(null)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  const started = useRef(false)
  const mounted = useRef(true)
  const startedCallback = useRef(onStarted)
  startedCallback.current = onStarted

  useEffect(() => {
    mounted.current = true

    function apply(event) {
      if (!mounted.current) return

      switch (event.event) {
        case 'progress':
          if (event.step) {
            setCurrentStep(event.step)
            setStepMessages(previous => ({ ...previous, [event.step]: event.message }))
          }
          if (event.stats) setStats(event.stats)
          break
        case 'step_complete':
          setResults(previous => ({ ...previous, [event.step]: event.result }))
          break
        case 'done':
          setCurrentStep('done')
          setPhase(STREAM_PHASES.done)
          break
        case 'error':
          setError(event.message)
          setPhase(STREAM_PHASES.error)
          break
        default:
          break
      }
    }

    async function run() {
      try {
        const { analysis_id: newAnalysisId } = await startAnalysis(repoFullName, language)
        startedCallback.current?.()

        if (mounted.current) {
          setAnalysisId(newAnalysisId)
          setPhase(STREAM_PHASES.streaming)
        }

        for await (const event of openAnalysisStream(newAnalysisId)) {
          apply(event)
        }
      } catch (caught) {
        if (!mounted.current) return
        setError(messageOf(caught))
        setPhase(STREAM_PHASES.error)
      }
    }

    if (!started.current) {
      started.current = true
      run()
    }

    return () => { mounted.current = false }
  }, [repoFullName, language])

  return { phase, currentStep, stepMessages, results, analysisId, stats, error }
}
