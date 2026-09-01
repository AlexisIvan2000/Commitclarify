import { describe, expect, it } from 'vitest'
import { loadScan } from '@test/fixtures'
import { analyzedFiles, chunkCoverage, coverageGaps, isComplete, shortSha } from '@features/scan/domain/coverage'

const react = loadScan('scan_react')
const petit = loadScan('scan_petit')

describe('couverture du scan', () => {
  it('considere une couverture absente comme complete', () => {
    expect(isComplete(null)).toBe(true)
    expect(coverageGaps(null)).toEqual([])
  })

  it('ne signale aucun manque sur un scan complet', () => {
    expect(isComplete({ ...petit.coverage, complete: petit.complete })).toBe(true)
    expect(coverageGaps({ ...petit.coverage, complete: petit.complete })).toEqual([])
  })

  it('remonte les fichiers plafonnes du scan react', () => {
    const gaps = coverageGaps({ ...react.coverage, complete: react.complete })

    expect(gaps).toContainEqual({ key: 'capped', count: 2309 })
  })

  it('additionne les echecs de recuperation', () => {
    const gaps = coverageGaps({
      complete: false, capped_over_limit: 0,
      fetch_failures: { timeout: 2, forbidden: 3 },
    })

    expect(gaps).toContainEqual({ key: 'failures', count: 5 })
  })

  it('compte les fichiers lus sur les fichiers suivis', () => {
    expect(analyzedFiles(react.coverage)).toEqual({ read: 496, tracked: 7199 })
  })

  it('ne devine pas un compte partiel', () => {
    expect(analyzedFiles({ fetched_files: 10 })).toBeNull()
  })

  it('raccourcit le sha a 7 caracteres', () => {
    expect(shortSha(react.coverage, null)).toBe('7dfc7cc')
    expect(shortSha(null, { repo_sha: 'abcdef1234' })).toBe('abcdef1')
    expect(shortSha(null, null)).toBeNull()
  })
})

describe('couverture des fragments indexes', () => {
  it('ne dit rien quand tout a ete indexe', () => {
    expect(chunkCoverage({ chunks: { complete: true, dropped: 0 } })).toBeNull()
    expect(chunkCoverage({})).toBeNull()
    expect(chunkCoverage(null)).toBeNull()
  })

  it('separe le delibere de l involontaire', () => {
    const result = chunkCoverage({
      chunks: {
        total: 1850, indexed: 1200, dropped: 650, complete: false,
        dropped_by_tier: { genere_ou_vendored: 520, tests: 130 },
      },
    })

    expect(result.deliberate).toBe(650)
    expect(result.involuntary).toBe(0)
  })

  it('compte le code source ecarte comme involontaire', () => {
    const result = chunkCoverage({
      chunks: {
        total: 2400, indexed: 1200, dropped: 1200, complete: false,
        dropped_by_tier: { genere_ou_vendored: 700, tests: 300, source: 200 },
      },
    })

    expect(result.involuntary).toBe(200)
    expect(result.tiers[0]).toEqual({ tier: 'genere_ou_vendored', count: 700 })
  })
})
