import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CATALOGS,
  SUPPORTED_LANGUAGES,
  detectLanguage,
  persistLanguage,
  setActiveLanguage,
} from './index'
import { LanguageContext } from './languageContext'

function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => setActiveLanguage(detectLanguage()))

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const changeLanguage = useCallback((next) => {
    const applied = setActiveLanguage(next)
    persistLanguage(applied)
    setLanguage(applied)
  }, [])

  const value = useMemo(
    () => ({
      language,
      strings: CATALOGS[language],
      available: SUPPORTED_LANGUAGES,
      changeLanguage,
    }),
    [language, changeLanguage],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export default LanguageProvider
