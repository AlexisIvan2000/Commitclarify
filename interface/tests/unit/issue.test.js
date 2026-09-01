import { describe, expect, it } from 'vitest'
import { issuesOf, loadScan } from '@test/fixtures'
import {
  foldBySeverity,
  groupIssues,
  isDismissed,
  normalizeIssue,
  normalizeIssues,
  severityRank,
  splitByVerdict,
} from '@features/scan/domain/issue'

const petit = loadScan('scan_petit')
const react = loadScan('scan_react')

const quality = normalizeIssues(issuesOf(petit.axes.quality_check))
const secrets = normalizeIssues(issuesOf(petit.axes.secrets_detection))

describe('normalizeIssue', () => {
  it('lit les lignes depuis les emplacements', () => {
    const issue = normalizeIssue({
      title: 'x', locations: [{ line: 3 }, { line: 7 }, { line: null }],
    })

    expect(issue.lines).toEqual([3, 7])
  })

  it('repere un fichier de test par son contexte', () => {
    expect(normalizeIssue({ title: 'x', context: 'test' }).isTestFile).toBe(true)
    expect(normalizeIssue({ title: 'x', context: null }).isTestFile).toBe(false)
  })

  it('retombe sur la description quand le titre manque', () => {
    expect(normalizeIssue({ description: 'sans titre' }).title).toBe('sans titre')
  })

  it('accepte une chaine nue', () => {
    expect(normalizeIssue('juste du texte').title).toBe('juste du texte')
  })

  it('ecarte ce qui n est pas une detection', () => {
    expect(normalizeIssue(null)).toBeNull()
    expect(normalizeIssues(undefined)).toEqual([])
  })

  it('garde la severite d origine d une retrogradation', () => {
    const issue = normalizeIssue({
      title: 'x', severity: 'info', original_severity: 'critical', verdict: 'false_positive',
    })

    expect(issue.severity).toBe('info')
    expect(issue.originalSeverity).toBe('critical')
  })
})

describe('groupIssues', () => {
  it('regroupe par regle ET par fichier', () => {
    expect(quality).toHaveLength(21)
    expect(groupIssues(quality)).toHaveLength(12)
  })

  it('fusionne les lignes consecutives d un meme fichier', () => {
    const appjsx = groupIssues(quality).find(e => e.filePath === 'interface/src/App.jsx')

    expect(appjsx.entries).toBe(7)
    expect(appjsx.occurrences).toBe(7)
    expect(appjsx.lines).toEqual([1, 2, 3, 4, 5, 6, 7])
  })

  it('ne fusionne jamais une meme regle a travers plusieurs fichiers', () => {
    const reactQuality = normalizeIssues(issuesOf(react.axes.quality_check))
    const unused = groupIssues(reactQuality).filter(e => e.rule === 'no-unused-vars')

    expect(unused).toHaveLength(3)
    expect(new Set(unused.map(e => e.filePath)).size).toBe(3)
  })

  it('additionne les occurrences plutot que de compter les entrees', () => {
    const reactQuality = normalizeIssues(issuesOf(react.axes.quality_check))
    const total = groupIssues(reactQuality).reduce((sum, e) => sum + e.occurrences, 0)

    expect(total).toBe(10)
  })

  it('trie par severite decroissante', () => {
    const ranks = groupIssues(quality).map(e => severityRank(e.severity))

    expect(ranks).toEqual([...ranks].sort((a, b) => a - b))
  })

  it('ne perd rien sur une liste vide', () => {
    expect(groupIssues([])).toEqual([])
  })
})

describe('foldBySeverity', () => {
  it('laisse 5 lignes principales sur l axe qualite', () => {
    const { main } = foldBySeverity(groupIssues(quality))

    expect(main).toHaveLength(5)
    expect(main.every(e => ['critical', 'high', 'medium'].includes(e.severity))).toBe(true)
  })

  it('replie Faible et Information dans deux pastilles', () => {
    const { folded } = foldBySeverity(groupIssues(quality))

    expect(folded.map(g => g.severity)).toEqual(['low', 'info'])
    expect(folded[0].entries).toHaveLength(6)
    expect(folded[0].detections).toBe(15)
  })

  it('ne replie rien quand aucune detection n est faible', () => {
    expect(foldBySeverity(groupIssues(secrets)).folded).toEqual([])
  })

  it('peut ne laisser aucune ligne principale', () => {
    const reactQuality = groupIssues(normalizeIssues(issuesOf(react.axes.quality_check)))
    const { main, folded } = foldBySeverity(reactQuality)

    expect(main).toHaveLength(0)
    expect(folded).toHaveLength(1)
    expect(folded[0].detections).toBe(10)
  })
})

describe('splitByVerdict', () => {
  it('sort les detections ecartees de la liste principale', () => {
    const issues = normalizeIssues([
      { id: 'a', title: 'gardee', severity: 'high' },
      { id: 'b', title: 'ecartee', severity: 'info', verdict: 'false_positive' },
    ])
    const { retained, dismissed } = splitByVerdict(issues)

    expect(retained.map(i => i.id)).toEqual(['a'])
    expect(dismissed.map(i => i.id)).toEqual(['b'])
    expect(isDismissed(dismissed[0])).toBe(true)
  })

  it('ne considere pas un verdict confirme comme ecarte', () => {
    const issues = normalizeIssues([{ id: 'a', title: 'x', verdict: 'confirmed' }])

    expect(splitByVerdict(issues).dismissed).toHaveLength(0)
  })
})
