import { useCallback, useEffect, useRef, useState } from 'react'
import { messageOf } from '../network/errors'

export default function useAsyncData(load) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const [attempt, setAttempt] = useState(0)
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true

    load()
      .then((data) => {
        if (alive.current) setState({ data, loading: false, error: null })
      })
      .catch((caught) => {
        if (alive.current) setState({ data: null, loading: false, error: messageOf(caught) })
      })

    return () => { alive.current = false }
  }, [load, attempt])

  const reload = useCallback(() => {
    setState(previous => ({ ...previous, loading: true, error: null }))
    setAttempt(previous => previous + 1)
  }, [])

  const setData = useCallback((updater) => {
    setState(previous => ({
      ...previous,
      data: typeof updater === 'function' ? updater(previous.data) : updater,
    }))
  }, [])

  return { ...state, reload, setData }
}
