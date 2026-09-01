import { useContext } from 'react'
import { RunsContext } from './runsContext'

export default function useRuns() {
  const context = useContext(RunsContext)
  if (!context) throw new Error('useRuns doit être utilisé dans un RunsProvider')
  return context
}
