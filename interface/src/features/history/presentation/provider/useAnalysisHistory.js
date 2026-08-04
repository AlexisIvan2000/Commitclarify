import { useCallback, useState } from 'react'
import { messageOf } from '@core/network/errors'
import useAsyncData from '@core/utils/useAsyncData'
import { deleteAllAnalyses, deleteAnalysis, fetchHistory } from '@features/scan/data/analysisApi'

export default function useAnalysisHistory() {
  const load = useCallback(() => fetchHistory(), [])
  const { data, loading, error, reload, setData } = useAsyncData(load)
  const [actionError, setActionError] = useState(null)

  const remove = useCallback(async (analysisId) => {
    setActionError(null)
    try {
      await deleteAnalysis(analysisId)
      setData(current => (current || []).filter(analysis => analysis.id !== analysisId))
    } catch (caught) {
      setActionError(messageOf(caught))
    }
  }, [setData])

  const removeAll = useCallback(async () => {
    setActionError(null)
    try {
      await deleteAllAnalyses()
      setData([])
    } catch (caught) {
      setActionError(messageOf(caught))
    }
  }, [setData])

  return {
    analyses: data || [],
    loading,
    error,
    actionError,
    reload,
    remove,
    removeAll,
  }
}
