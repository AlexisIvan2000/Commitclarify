import en from '../src/core/translation/en.js'
import fr from '../src/core/translation/fr.js'

const CATALOGS = { fr, en }

function paths(value, prefix = '') {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => paths(item, `${prefix}[${index}]`))
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, child]) =>
      paths(child, prefix ? `${prefix}.${key}` : key),
    )
  }
  return [prefix]
}

const reference = paths(fr)
const problems = []

for (const [language, catalog] of Object.entries(CATALOGS)) {
  const found = new Set(paths(catalog))

  for (const path of reference) {
    if (!found.has(path)) problems.push(`${language} : cle manquante ${path}`)
  }
  for (const path of found) {
    if (!reference.includes(path)) problems.push(`${language} : cle en trop ${path}`)
  }
}

const empty = Object.entries(CATALOGS).flatMap(([language, catalog]) =>
  paths(catalog)
    .filter((path) => {
      const value = path
        .replace(/\[(\d+)\]/g, '.$1')
        .split('.')
        .reduce((node, key) => node?.[key], catalog)
      return typeof value === 'string' && !value.trim()
    })
    .map((path) => `${language} : valeur vide ${path}`),
)

const all = [...problems, ...empty]

if (all.length) {
  console.error(all.join('\n'))
  process.exit(1)
}

console.log(`Traductions coherentes : ${reference.length} cles x ${Object.keys(CATALOGS).length} langues`)
