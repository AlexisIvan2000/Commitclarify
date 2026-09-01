import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@features/scan/data/analysisApi', () => ({
  fetchActiveRun: vi.fn(),
  startAnalysis: vi.fn(),
  openAnalysisStream: vi.fn(),
  openDeepenStream: vi.fn(),
  fetchAnalysis: vi.fn(),
}))

const { fetchActiveRun } = await import('@features/scan/data/analysisApi')
const { default: RunsProvider } = await import('@features/scan/presentation/provider/RunsProvider')
const { default: useRuns } = await import('@features/scan/presentation/provider/useRuns')

function Probe() {
  const { run, busy, ready } = useRuns()
  return (
    <span data-testid="state">
      {`${ready ? 'pret' : 'attente'}|${busy ? 'occupe' : 'libre'}|${run?.repoFullName ?? 'aucun'}`}
    </span>
  )
}

beforeEach(() => { vi.clearAllMocks() })

describe('RunsProvider', () => {
  it('se monte sans planter', async () => {
    fetchActiveRun.mockResolvedValue(null)

    render(<RunsProvider><Probe /></RunsProvider>)

    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('pret|libre|aucun'))
  })

  it('reste utilisable quand le serveur ne repond pas', async () => {
    fetchActiveRun.mockRejectedValue(new Error('hors ligne'))

    render(<RunsProvider><Probe /></RunsProvider>)

    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('pret|libre|aucun'))
  })

  it('ne demande la course active qu une seule fois', async () => {
    fetchActiveRun.mockResolvedValue(null)

    const { rerender } = render(<RunsProvider><Probe /></RunsProvider>)
    await waitFor(() => expect(screen.getByTestId('state')).toHaveTextContent('pret'))
    rerender(<RunsProvider><Probe /></RunsProvider>)

    expect(fetchActiveRun).toHaveBeenCalledTimes(1)
  })
})
