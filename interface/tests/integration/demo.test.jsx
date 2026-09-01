import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LanguageContext } from '@core/translation/languageContext'
import { normalizeIssues } from '@features/scan/domain/issue'
import { resultsByAspect } from '@features/scan/domain/report'
import { ANALYSIS_STEPS } from '@features/scan/domain/steps'
import AnalysisReport from '@features/report/presentation/components/AnalysisReport'
import { french } from '@test/fixtures'
import fixture from '@features/report/demo/reactScan.json'

function show(analysis) {
  return render(
    <LanguageContext.Provider value={french}>
      <AnalysisReport analysis={analysis} results={resultsByAspect(analysis)} />
    </LanguageContext.Provider>,
  )
}

const allIssues = analysis => Object.values(resultsByAspect(analysis))
  .flatMap(result => normalizeIssues(result.issues))

describe.each(['base', 'sorted'])('demo publique, variante %s', (variant) => {
  const analysis = fixture[variant]

  it('porte le depot annonce', () => {
    expect(analysis.repo_name).toBe('facebook/react')
  })

  it('contient les quatre axes', () => {
    const byAspect = resultsByAspect(analysis)
    expect(ANALYSIS_STEPS.every(aspect => byAspect[aspect])).toBe(true)
  })

  it('rend le rapport complet', () => {
    const { container } = show(analysis)
    expect(container.textContent.length).toBeGreaterThan(500)
  })

  it('montre les .env critiques', () => {
    const { container } = show(analysis)
    expect(container.textContent).toContain('fixtures/fiber-debugger/.env')
  })

  it('annonce la couverture partielle', () => {
    const { container } = show(analysis)
    expect(container.textContent.replace(/[^0-9]/g, '')).toContain('2309')
  })

  it('donne un titre et une severite a chaque detection', () => {
    const issues = allIssues(analysis)
    expect(issues.length).toBeGreaterThan(0)
    expect(issues.every(issue => issue.title && issue.severity)).toBe(true)
  })
})

describe('demo publique, specificites du tri IA', () => {
  it('n ecarte rien dans la variante brute', () => {
    expect(allIssues(fixture.base).filter(i => i.verdict)).toHaveLength(0)
  })

  it('ecarte cinq detections dans la variante triee', () => {
    const dismissed = allIssues(fixture.sorted).filter(i => i.verdict === 'false_positive')
    expect(dismissed).toHaveLength(5)
  })

  it('conserve la severite d origine des detections ecartees', () => {
    const dismissed = allIssues(fixture.sorted).filter(i => i.verdict === 'false_positive')
    expect(dismissed.every(i => i.severity === 'info' && i.originalSeverity)).toBe(true)
  })

  it('garde au moins un verdict confirme', () => {
    expect(allIssues(fixture.sorted).some(i => i.verdict === 'confirmed')).toBe(true)
  })

  it('replie les detections ecartees', () => {
    const { container } = show(fixture.sorted)
    expect(container.textContent).toContain('écartée')
  })
})
