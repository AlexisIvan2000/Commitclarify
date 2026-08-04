import { useCallback } from 'react'
import useAsyncData from '@core/utils/useAsyncData'
import { fetchAnalysis } from '@features/scan/data/analysisApi'

export default function useAnalysisDetail(analysisId) {
  const load = useCallback(() => fetchAnalysis(analysisId), [analysisId])
  const { data, loading, error, reload } = useAsyncData(load)

  return { analysis: data, loading, error, reload }
}
