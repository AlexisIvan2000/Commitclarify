import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, NetworkError } from '@core/network/errors'
import * as api from '@features/scan/data/analysisApi'
import followRun, { RUN_OUTCOMES } from '@features/scan/presentation/provider/followRun'

const PROGRESS = { event: 'progress', step: 'fetching' }
const DONE = { event: 'done' }
const FAILURE = { event: 'error', message: 'boum' }

function streamOf(...batches) {
  let call = 0
  return async function* open() {
    const batch = batches[Math.min(call, batches.length - 1)]
    call += 1
    if (batch instanceof Error) throw batch
    for (const event of batch) yield event
  }
}

function collector() {
  const seen = []
  return { seen, onEvent: event => seen.push(event.event) }
}

let analysisStates

beforeEach(() => {
  analysisStates = []
  vi.spyOn(api, 'fetchAnalysis').mockImplementation(
    async () => ({ id: 'a1', repo_name: 'owner/repo', status: analysisStates.shift() ?? 'scanned' }),
  )
  vi.spyOn(globalThis, 'setTimeout').mockImplementation(fn => { fn(); return 0 })
})

afterEach(() => { vi.restoreAllMocks() })

function follow(openStream, signal = new AbortController().signal) {
  const { seen, onEvent } = collector()
  return followRun({ analysisId: 'a1', openStream, onEvent, signal }).then(r => ({ ...r, seen }))
}

describe('followRun', () => {
  it('rend le resultat quand le flux va jusqu au bout', async () => {
    const { outcome, analysis, seen } = await follow(streamOf([PROGRESS, DONE]))

    expect(outcome).toBe(RUN_OUTCOMES.done)
    expect(analysis.id).toBe('a1')
    expect(seen).not.toContain('reconnecting')
  })

  it('remonte un echec annonce par le serveur', async () => {
    const { outcome, seen } = await follow(streamOf([PROGRESS, FAILURE]))

    expect(outcome).toBe(RUN_OUTCOMES.failed)
    expect(seen.at(-1)).toBe('error')
  })

  it('se rebranche quand le flux tombe sans verdict', async () => {
    analysisStates = ['scanning']
    const { outcome, seen } = await follow(streamOf([PROGRESS], [PROGRESS, DONE]))

    expect(outcome).toBe(RUN_OUTCOMES.done)
    expect(seen).toContain('reconnecting')
    expect(seen.filter(e => e === 'progress')).toHaveLength(2)
  })

  it('adopte le resultat quand le serveur a deja fini', async () => {
    analysisStates = ['scanned']
    const { outcome, seen } = await follow(streamOf([PROGRESS]))

    expect(outcome).toBe(RUN_OUTCOMES.done)
    expect(seen.at(-1)).toBe('done')
  })

  it('adopte l echec quand le serveur a echoue', async () => {
    analysisStates = ['failed']
    const { outcome, seen } = await follow(streamOf([PROGRESS]))

    expect(outcome).toBe(RUN_OUTCOMES.failed)
    expect(seen.at(-1)).toBe('error')
  })

  it('se rebranche apres une erreur reseau', async () => {
    analysisStates = ['scanning']
    const { outcome } = await follow(streamOf(new NetworkError(new Error('socket')), [PROGRESS, DONE]))

    expect(outcome).toBe(RUN_OUTCOMES.done)
  })

  it('abandonne apres un budget borne de reprises', async () => {
    analysisStates = Array(20).fill('scanning')
    const { outcome, seen } = await follow(streamOf([PROGRESS]))

    expect(outcome).toBe(RUN_OUTCOMES.lost)
    expect(seen.filter(e => e === 'reconnecting')).toHaveLength(5)
  })

  it('rearme le budget quand de nouveaux evenements arrivent', async () => {
    analysisStates = Array(20).fill('scanning')
    const { seen } = await follow(streamOf([PROGRESS], [PROGRESS, PROGRESS], [PROGRESS, PROGRESS]))

    expect(seen.filter(e => e === 'reconnecting').length).toBeGreaterThan(5)
  })

  it('s arrete net quand on abandonne', async () => {
    const controller = new AbortController()
    controller.abort()
    const { outcome } = await follow(streamOf([PROGRESS, DONE]), controller.signal)

    expect(outcome).toBe(RUN_OUTCOMES.aborted)
  })

  it('ne reessaie pas sur un refus de cadence', async () => {
    await expect(follow(streamOf(new ApiError(429, 'trop vite', 'scan_throttled'))))
      .rejects.toMatchObject({ status: 429 })
  })

  it('ne reessaie pas sur un acces refuse', async () => {
    await expect(follow(streamOf(new ApiError(403, 'non', 'forbidden'))))
      .rejects.toMatchObject({ status: 403 })
  })

  it('ignore les battements de coeur dans le budget', async () => {
    analysisStates = Array(20).fill('scanning')
    const { seen } = await follow(streamOf([{ event: 'ping' }]))

    expect(seen.filter(e => e === 'reconnecting')).toHaveLength(5)
  })

  it('remonte l erreur d origine quand le serveur ne repond plus non plus', async () => {
    api.fetchAnalysis.mockRejectedValue(new ApiError(500, 'casse', 'internal_error'))

    await expect(follow(streamOf(new NetworkError(new Error('socket')))))
      .rejects.toBeInstanceOf(NetworkError)
  })
})
