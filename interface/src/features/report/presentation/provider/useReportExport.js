import { useCallback, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { saveBlob } from '@core/utils/download'
import { downloadReport } from '@features/scan/data/analysisApi'

export default function useReportExport(analysisId) {
  const [pendingFormat, setPendingFormat] = useState(null)
  const [error, setError] = useState(null)

  const exportReport = useCallback(async (format) => {
    setError(null)
    setPendingFormat(format)

    try {
      const { blob, filename } = await downloadReport(analysisId, format)
      saveBlob(blob, filename || `commitclarify_${analysisId}.${format}`)
    } catch (caught) {
      setError(messageOf(caught))
    } finally {
      setPendingFormat(null)
    }
  }, [analysisId])

  return { exportReport, pendingFormat, error }
}
