import { describe, expect, it } from 'vitest'
import { languageColor } from '@features/repositories/domain/languageColor'
import { FAILED, NEVER, RUNNING, lastScanByRepo, scanState } from '@features/repositories/domain/lastScan'

const at = hours => new Date(Date.now() - hours * 3600 * 1000).toISOString()

describe('lastScanByRepo', () => {
  it('garde le scan le plus recent par depot', () => {
    const latest = lastScanByRepo([
      { repo_name: 'a/b', status: 'failed', created_at: at(10) },
      { repo_name: 'a/b', status: 'scanned', created_at: at(1) },
      { repo_name: 'c/d', status: 'completed', created_at: at(3) },
    ])

    expect(latest.get('a/b').status).toBe('scanned')
    expect(latest.get('c/d').status).toBe('completed')
    expect(latest.size).toBe(2)
  })

  it('ne renvoie rien pour un depot jamais scanne', () => {
    expect(lastScanByRepo([]).get('a/b')).toBeUndefined()
  })
})

describe('scanState', () => {
  it('traite l absence d analyse comme jamais scanne', () => {
    expect(scanState(undefined).state).toBe(NEVER)
  })

  it('reconnait les etats en vol', () => {
    for (const status of ['pending', 'scanning', 'analyzing', 'processing']) {
      expect(scanState({ status }).state).toBe(RUNNING)
    }
  })

  it('reconnait un echec', () => {
    expect(scanState({ status: 'failed' }).state).toBe(FAILED)
  })

  it('retombe sur jamais scanne pour un statut inconnu', () => {
    expect(scanState({ status: 'zzz' }).state).toBe(NEVER)
  })
})

describe('languageColor', () => {
  it('donne sa couleur a un langage connu, insensible a la casse', () => {
    expect(languageColor('Python')).toBe(languageColor('python'))
    expect(languageColor('Python')).toMatch(/^#/)
  })

  it('reste neutre pour l inconnu et pour rien', () => {
    expect(languageColor('Brainfuck')).toBe('var(--ink-ghost)')
    expect(languageColor(null)).toBe('var(--ink-ghost)')
  })
})
