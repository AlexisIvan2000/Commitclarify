import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { requestJson } from '@core/network/apiClient'
import { clearTokens, storeTokens } from '@core/network/tokenStorage'

function ok(body = {}) {
  return { ok: true, status: 200, json: async () => body, headers: new Headers() }
}

function status(code) {
  return { ok: false, status: code, json: async () => ({ detail: 'x' }), headers: new Headers() }
}

let fetchMock

beforeEach(() => {
  clearTokens()
  storeTokens({ access_token: 'a', refresh_token: 'r' })
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  vi.spyOn(globalThis, 'setTimeout').mockImplementation((fn) => { fn(); return 0 })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('reprise des pannes transitoires', () => {
  it('rejoue un 502 et rend la reponse suivante', async () => {
    fetchMock.mockResolvedValueOnce(status(502)).mockResolvedValueOnce(ok({ id: 'a1' }))

    await expect(requestJson('/analyze/history')).resolves.toEqual({ id: 'a1' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('rejoue aussi 503 et 504', async () => {
    fetchMock
      .mockResolvedValueOnce(status(503))
      .mockResolvedValueOnce(status(504))
      .mockResolvedValueOnce(ok({ ok: true }))

    await expect(requestJson('/analyze/history')).resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('rejoue une panne reseau', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce(ok({ ok: 1 }))

    await expect(requestJson('/analyze/history')).resolves.toEqual({ ok: 1 })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('abandonne apres avoir epuise son budget', async () => {
    fetchMock.mockResolvedValue(status(502))

    await expect(requestJson('/analyze/history')).rejects.toMatchObject({ status: 502 })
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it('ne rejoue jamais une ecriture', async () => {
    fetchMock.mockResolvedValue(status(502))

    await expect(requestJson('/analyze/history/all', { method: 'DELETE' }))
      .rejects.toMatchObject({ status: 502 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('ne rejoue pas une erreur definitive', async () => {
    fetchMock.mockResolvedValue(status(404))

    await expect(requestJson('/analyze/x')).rejects.toMatchObject({ status: 404 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('ne rejoue pas une requete abandonnee', async () => {
    const controller = new AbortController()
    controller.abort()
    fetchMock.mockResolvedValue(status(502))

    await expect(requestJson('/analyze/history', { signal: controller.signal }))
      .rejects.toMatchObject({ status: 502 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
