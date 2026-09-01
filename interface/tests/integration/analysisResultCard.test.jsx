import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LanguageContext } from '@core/translation/languageContext'
import { french, loadScan, resultOf } from '@test/fixtures'
import AnalysisResultCard from '@features/report/presentation/components/AnalysisResultCard'

const petit = loadScan('scan_petit')
const react = loadScan('scan_react')

function show(aspect, axisResult, coverage = null) {
  return render(
    <LanguageContext.Provider value={french}>
      <AnalysisResultCard aspect={aspect} result={resultOf(axisResult)} pending={false} coverage={coverage} />
    </LanguageContext.Provider>,
  )
}

const rows = container => container.querySelectorAll('.issue-row').length
const chips = container => container.querySelectorAll('.folded-toggle').length

describe('axe qualite, le plus dense', () => {
  it('ne montre que les 5 detections qui meritent l attention', () => {
    const { container } = show('quality_check', petit.axes.quality_check)

    expect(rows(container)).toBe(5)
    expect(chips(container)).toBe(2)
  })

  it('annonce le volume replie', () => {
    show('quality_check', petit.axes.quality_check)

    expect(screen.getByText(/15 détections en 6 entrées/)).toBeInTheDocument()
  })

  it('ne laisse fuir aucune detection faible dans la liste principale', () => {
    const { container } = show('quality_check', petit.axes.quality_check)

    expect(container.textContent).not.toContain('interface/src/App.jsx')
    expect(container.textContent).not.toContain('Ligne trop longue')
  })
})

describe('axe secrets', () => {
  it('ne replie rien quand tout est critique ou eleve', () => {
    const { container } = show('secrets_detection', petit.axes.secrets_detection)

    expect(rows(container)).toBe(6)
    expect(chips(container)).toBe(0)
  })

  it('badge les fichiers de test sans affaiblir la severite', () => {
    const { container } = show('secrets_detection', petit.axes.secrets_detection)

    expect(container.textContent).toContain('Fichier de test')
    expect(rows(container)).toBe(6)
  })
})

describe('axe partiel', () => {
  it('affiche la note de couverture', () => {
    const coverage = { ...react.coverage, complete: react.complete }
    const { container } = show('secrets_detection', react.axes.secrets_detection, coverage)

    expect(container.querySelector('.coverage-note')).not.toBeNull()
    expect(container.textContent.replace(/[^0-9]/g, '')).toContain('2309')
  })

  it('peut n avoir aucune ligne principale', () => {
    const { container } = show('quality_check', react.axes.quality_check)

    expect(rows(container)).toBe(0)
    expect(chips(container)).toBe(1)
  })
})
