import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { getStrings } from '@core/translation'
import {
  fetchActiveRun,
  openAnalysisStream,
  openDeepenStream,
  startAnalysis,
} from '../../data/analysisApi'
import { DEEPEN, SCAN, slowThreshold } from '../../domain/runs'
import followRun, { RUN_OUTCOMES } from './followRun'
import { RunsContext } from './runsContext'
import { STREAM_PHASES, emptyStreamState, reduceEvent } from './streamEvents'

const OPEN_STREAM = {
  [SCAN]: openAnalysisStream,
  [DEEPEN]: openDeepenStream,
}

const DONE_KEY = {
  [SCAN]: 'scanDone',
  [DEEPEN]: 'deepenDone',
}

function freshRun(kind, analysisId, repoFullName) {
  return {
    kind,
    analysisId,
    repoFullName,
    slow: false,
    analysis: null,
    ...emptyStreamState(STREAM_PHASES.streaming),
  }
}

function RunsProvider({ children }) {
  const [run, setRun] = useState(null)
  const [notice, setNotice] = useState(null)
  const [ready, setReady] = useState(false)

  const inFlight = useRef(false)
  const rehydrated = useRef(false)
  const connection = useRef(null)
  const slowTimer = useRef(null)

  const stopTimer = useCallback(() => {
    if (slowTimer.current) clearTimeout(slowTimer.current)
    slowTimer.current = null
  }, [])

  useEffect(() => () => {
    connection.current?.abort()
    if (slowTimer.current) clearTimeout(slowTimer.current)
  }, [])

  useEffect(() => {
    if (rehydrated.current) return
    rehydrated.current = true

    let abandoned = false

    fetchActiveRun()
      .then(active => {
        if (abandoned || !active) return

        inFlight.current = true
        setRun(freshRun(active.kind, active.analysis_id, active.repo_name))
        follow(active.kind, active.analysis_id, active.repo_name)
          .finally(() => { inFlight.current = false })
      })
      .catch(() => {})
      .finally(() => { if (!abandoned) setReady(true) })

    return () => { abandoned = true }
  }, [follow])

  const follow = useCallback(async (kind, analysisId, repoFullName) => {
    const controller = new AbortController()
    connection.current = controller

    slowTimer.current = setTimeout(
      () => setRun(previous => (previous ? { ...previous, slow: true } : previous)),
      slowThreshold(kind) * 1000,
    )

    try {
      const { outcome, analysis } = await followRun({
        analysisId,
        openStream: OPEN_STREAM[kind],
        onEvent: event => setRun(previous => (previous ? reduceEvent(previous, event) : previous)),
        signal: controller.signal,
      })

      if (controller.signal.aborted) return null

      if (outcome === RUN_OUTCOMES.lost) {
        setRun(previous => (previous ? {
          ...previous,
          slow: false,
          reconnecting: false,
          recoverable: true,
          phase: STREAM_PHASES.error,
          error: getStrings().errors.streamLost,
        } : previous))
        return null
      }

      const failed = outcome === RUN_OUTCOMES.failed
      const strings = getStrings()

      setRun(previous => (previous ? { ...previous, slow: false, analysis } : previous))
      setNotice({
        kind,
        analysisId,
        repoFullName,
        tone: failed ? 'error' : 'success',
        message: failed ? strings.runs.failed : strings.runs[DONE_KEY[kind]],
      })

      return failed ? null : analysis
    } catch (caught) {
      if (controller.signal.aborted) return null

      const message = messageOf(caught)
      setRun(previous => (previous ? {
        ...previous, slow: false, phase: STREAM_PHASES.error, error: message,
      } : previous))
      setNotice({ kind, analysisId, repoFullName, tone: 'error', message })
      return null
    } finally {
      stopTimer()
      if (connection.current === controller) connection.current = null
    }
  }, [stopTimer])

  const startScan = useCallback(async (repoFullName, language) => {
    if (inFlight.current) return null
    inFlight.current = true

    setNotice(null)
    setRun(freshRun(SCAN, null, repoFullName))

    try {
      const { analysis_id: analysisId } = await startAnalysis(repoFullName, language)
      setRun(previous => (previous ? { ...previous, analysisId } : previous))
      return await follow(SCAN, analysisId, repoFullName)
    } catch (caught) {
      const message = messageOf(caught)
      setRun(previous => (previous ? {
        ...previous, phase: STREAM_PHASES.error, error: message,
      } : previous))
      setNotice({ kind: SCAN, analysisId: null, repoFullName, tone: 'error', message })
      return null
    } finally {
      inFlight.current = false
    }
  }, [follow])

  const startDeepen = useCallback(async (analysisId, repoFullName) => {
    if (inFlight.current) return null
    inFlight.current = true

    setNotice(null)
    setRun(freshRun(DEEPEN, analysisId, repoFullName))

    try {
      return await follow(DEEPEN, analysisId, repoFullName)
    } finally {
      inFlight.current = false
    }
  }, [follow])

  const release = useCallback(() => {
    connection.current?.abort()
    connection.current = null
    stopTimer()
    inFlight.current = false
    setRun(null)
  }, [stopTimer])

  const dismissNotice = useCallback(() => setNotice(null), [])

  const value = useMemo(() => ({
    run,
    notice,
    ready,
    busy: run !== null && run.phase === STREAM_PHASES.streaming,
    startScan,
    startDeepen,
    release,
    dismissNotice,
  }), [run, notice, ready, startScan, startDeepen, release, dismissNotice])

  return <RunsContext.Provider value={value}>{children}</RunsContext.Provider>
}

export default RunsProvider
