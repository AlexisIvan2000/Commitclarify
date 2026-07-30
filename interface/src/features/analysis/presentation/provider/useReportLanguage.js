import { useCallback, useState } from 'react'
import { DEFAULT_LANGUAGE, normalizeLanguage } from '@core/translation'
import { useLanguage } from '@core/translation/useTranslation'

const STORAGE_KEY = 'report_language'

export default function useReportLanguage() {
  const { language } = useLanguage()
  const [chosen, setChosen] = useState(
    () => normalizeLanguage(localStorage.getItem(STORAGE_KEY)),
  )

  const setReportLanguage = useCallback((next) => {
    const applied = normalizeLanguage(next) || DEFAULT_LANGUAGE
    localStorage.setItem(STORAGE_KEY, applied)
    setChosen(applied)
  }, [])

  return { reportLanguage: chosen || language, setReportLanguage }
}
