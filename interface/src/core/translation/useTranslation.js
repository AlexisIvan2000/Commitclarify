import { useContext } from 'react'
import { getStrings } from './index'
import { LanguageContext } from './languageContext'

export default function useTranslation() {
  const context = useContext(LanguageContext)
  return context ? context.strings : getStrings()
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('useLanguage doit être utilisé dans un LanguageProvider')
  return context
}
