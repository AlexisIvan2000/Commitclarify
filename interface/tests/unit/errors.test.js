import { describe, expect, it } from 'vitest'
import { setActiveLanguage } from '@core/translation'
import { ApiError, NetworkError, fillParams, messageForCode, messageOf } from '@core/network/errors'

setActiveLanguage('fr')

describe('interpolation des messages', () => {
  it('remplace chaque parametre', () => {
    expect(fillParams('{a} et {b}', { a: 'un', b: 'deux' })).toBe('un et deux')
  })

  it('remplace toutes les occurrences', () => {
    expect(fillParams('{x} {x}', { x: '1' })).toBe('1 1')
  })

  it('laisse le gabarit intact sans parametres', () => {
    expect(fillParams('rien', null)).toBe('rien')
  })
})

describe('resolution par code', () => {
  it('traduit un code connu', () => {
    expect(messageForCode('analysis_finished')).toContain('déjà terminée')
  })

  it('injecte le delai dans le message de cadence', () => {
    expect(messageForCode('scan_throttled', { seconds: 37 })).toContain('37')
  })

  it('injecte la limite dans le message de quota', () => {
    expect(messageForCode('quota_exceeded', { limit: 3 })).toContain('3')
  })

  it('ne renvoie rien pour un code inconnu', () => {
    expect(messageForCode('code_qui_n_existe_pas')).toBeNull()
    expect(messageForCode(null)).toBeNull()
  })
})

describe('messageOf', () => {
  it('prefere la traduction par code au detail du serveur', () => {
    const error = new ApiError(429, 'Too many scans started in a row.', 'scan_throttled', { seconds: 12 })

    expect(messageOf(error)).toContain('12')
    expect(messageOf(error)).not.toContain('Too many')
  })

  it('retombe sur le detail du serveur quand le code est inconnu', () => {
    expect(messageOf(new ApiError(400, 'detail brut', 'code_inconnu'))).toBe('detail brut')
  })

  it('retombe sur le statut quand il n y a ni code ni detail', () => {
    expect(messageOf(new ApiError(404, null, null))).toBeTruthy()
  })

  it('a un message dedie pour la panne reseau', () => {
    expect(messageOf(new NetworkError(new Error('x')))).toBeTruthy()
  })
})
