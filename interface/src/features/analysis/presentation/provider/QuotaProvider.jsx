import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchQuota } from '../../data/analysisApi'
import { QuotaContext } from './quotaContext'

function QuotaProvider({ enabled, children }) {
  const [quota, setQuota] = useState(null)

  const refresh = useCallback(() => {
    if (!enabled) return
    fetchQuota().then(setQuota).catch(() => {})
  }, [enabled])

  useEffect(() => {
    refresh()
  }, [refresh])

  const value = useMemo(
    () => ({ quota: enabled ? quota : null, refresh }),
    [enabled, quota, refresh],
  )

  return <QuotaContext.Provider value={value}>{children}</QuotaContext.Provider>
}

export default QuotaProvider
