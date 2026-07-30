import en from './en'
import fr from './fr'

export const CATALOGS = { fr, en }
export const SUPPORTED_LANGUAGES = ['fr', 'en']
export const DEFAULT_LANGUAGE = 'en'

const STORAGE_KEY = 'ui_language'

export function normalizeLanguage(value) {
  if (!value) return null

  const candidate = String(value).trim().toLowerCase().replace('_', '-').split('-')[0]
  return SUPPORTED_LANGUAGES.includes(candidate) ? candidate : null
}

export function detectLanguage() {
  const stored = normalizeLanguage(localStorage.getItem(STORAGE_KEY))
  if (stored) return stored

  const candidates = navigator.languages?.length ? navigator.languages : [navigator.language]
  for (const candidate of candidates) {
    const match = normalizeLanguage(candidate)
    if (match) return match
  }

  return DEFAULT_LANGUAGE
}

export function persistLanguage(language) {
  localStorage.setItem(STORAGE_KEY, language)
}

let activeLanguage = detectLanguage()

export function getLanguage() {
  return activeLanguage
}

export function setActiveLanguage(language) {
  activeLanguage = normalizeLanguage(language) || DEFAULT_LANGUAGE
  return activeLanguage
}

export function getStrings() {
  return CATALOGS[activeLanguage]
}
