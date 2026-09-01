import { execFileSync } from 'node:child_process'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const work = join(root, 'node_modules', '.cache', 'cc-demo')
mkdirSync(work, { recursive: true })
const entry = join(work, 'entry.jsx')
const bundle = join(work, 'bundle.cjs')
const stub = join(work, 'stub.cjs')

writeFileSync(stub, `
const store = new Map()
globalThis.localStorage = { getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) }
globalThis.navigator = globalThis.navigator || { language: 'fr' }
globalThis.__VITE_ENV = { VITE_API_URL: 'http://demo.test' }
`)

writeFileSync(entry, `
import { renderToStaticMarkup } from 'react-dom/server'
import { LanguageContext } from '@core/translation/languageContext'
import { CATALOGS } from '@core/translation'
import AnalysisReport from '@features/report/presentation/components/AnalysisReport'
import { resultsByAspect } from '@features/scan/domain/report'
import { normalizeIssues, splitByVerdict } from '@features/scan/domain/issue'
import { ANALYSIS_STEPS } from '@features/scan/domain/steps'
import fixture from '@features/report/demo/reactScan.json'

const fr = { language: 'fr', strings: CATALOGS.fr, changeLanguage: () => {} }
const render = a => renderToStaticMarkup(
  <LanguageContext.Provider value={fr}><AnalysisReport analysis={a} results={resultsByAspect(a)} /></LanguageContext.Provider>,
)

let bad = 0
const check = (label, ok, detail) => {
  if (!ok) bad += 1
  console.log(\`\${ok ? '  ok  ' : '  ECHEC'} \${label}\${ok ? '' : \` (\${detail})\`}\`)
}

for (const variant of ['base', 'sorted']) {
  const analysis = fixture[variant]
  check(\`\${variant} : le depot est facebook/react\`, analysis.repo_name === 'facebook/react', analysis.repo_name)
  check(\`\${variant} : les 4 axes sont presents\`,
    ANALYSIS_STEPS.every(a => resultsByAspect(analysis)[a]), 'axe manquant')

  const html = render(analysis)
  check(\`\${variant} : le rapport rend\`, html.length > 2000, html.length)
  check(\`\${variant} : les .env critiques apparaissent\`,
    html.includes('fixtures/fiber-debugger/.env'), 'detection absente')
  const digits = html.replace(/[^0-9]/g, '')
  check(\`\${variant} : la couverture partielle est annoncee\`,
    digits.includes('2309') && html.includes('non lus'), 'couverture absente')

  const issues = Object.values(resultsByAspect(analysis)).flatMap(r => normalizeIssues(r.issues))
  check(\`\${variant} : chaque detection a un titre et une severite\`,
    issues.length > 0 && issues.every(i => i.title && i.severity), 'champ manquant')

  if (variant === 'sorted') {
    const dismissed = issues.filter(i => i.verdict === 'false_positive')
    check('sorted : des detections sont ecartees', dismissed.length === 5, dismissed.length)
    check('sorted : elles gardent leur severite d origine',
      dismissed.every(i => i.originalSeverity && i.severity === 'info'), 'retrogradation incomplete')
    check('sorted : le repli des ecartees est rendu',
      html.includes('écartée'), 'repli absent')
    check('sorted : un verdict confirme existe',
      issues.some(i => i.verdict === 'confirmed'), 'aucun confirme')
  } else {
    const { dismissed } = splitByVerdict(issues)
    check('base : aucune detection ecartee', dismissed.length === 0, dismissed.length)
  }
}

console.log(bad === 0 ? 'Demo conforme' : \`\${bad} verification(s) en echec\`)
process.exit(bad === 0 ? 0 : 1)
`)

try {
  execFileSync('npx', ['esbuild', entry,
    '--bundle', '--format=cjs', '--platform=node', '--jsx=automatic',
    '--alias:@core=./src/core', '--alias:@features=./src/features',
    '--define:import.meta.env=globalThis.__VITE_ENV',
    '--external:react', '--external:react-dom', '--external:react-dom/server',
    '--external:react/jsx-runtime', '--external:react-router-dom',
    '--loader:.css=empty', `--outfile=${bundle}`,
  ], { cwd: root, stdio: ['ignore', 'ignore', 'inherit'], shell: process.platform === 'win32' })

  execFileSync(process.execPath, ['-r', stub, bundle], { cwd: root, stdio: 'inherit' })
} finally {
  rmSync(work, { recursive: true, force: true })
}
