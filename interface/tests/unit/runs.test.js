import { describe, expect, it } from 'vitest'
import { DEEPEN, SCAN, shouldStartScan, slowThreshold } from '@features/scan/domain/runs'

const base = {
  ready: true, repoFullName: 'owner/repo', followsThisRepo: false, somethingRunning: false,
}

describe('shouldStartScan', () => {
  it('attend la fin de la rehydratation', () => {
    expect(shouldStartScan({ ...base, ready: false })).toBe(false)
  })

  it('ne relance pas quand le run affiche est deja le notre', () => {
    expect(shouldStartScan({ ...base, followsThisRepo: true })).toBe(false)
  })

  it('ne demarre pas pendant qu un autre run tourne', () => {
    expect(shouldStartScan({ ...base, somethingRunning: true })).toBe(false)
  })

  it('ne demarre pas sans depot dans l URL', () => {
    expect(shouldStartScan({ ...base, repoFullName: null })).toBe(false)
  })

  it('demarre quand rien ne tourne', () => {
    expect(shouldStartScan(base)).toBe(true)
  })

  it('demarre malgre un run termine sur un autre depot', () => {
    expect(shouldStartScan({ ...base, followsThisRepo: false, somethingRunning: false })).toBe(true)
  })
})

describe('slowThreshold', () => {
  it('laisse plus de temps a l analyse IA qu au scan', () => {
    expect(slowThreshold(DEEPEN)).toBeGreaterThan(slowThreshold(SCAN))
  })

  it('retombe sur le seuil du scan pour une phase inconnue', () => {
    expect(slowThreshold('inconnu')).toBe(slowThreshold(SCAN))
  })
})
