import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@core/network/errors'
import { clearTokens, getAccessToken, storeTokens } from '@core/network/tokenStorage'

vi.mock('@features/authentication/data/authApi', () => ({
  fetchCurrentUser: vi.fn(),
  exchangeAuthCode: vi.fn(),
  revokeSession: vi.fn(),
  deleteAccount: vi.fn(),
  getLoginUrl: () => 'https://github.test/login',
}))

const { fetchCurrentUser } = await import('@features/authentication/data/authApi')
const { default: AuthProvider } = await import('@features/authentication/presentation/provider/AuthProvider')
const { default: useAuth } = await import('@features/authentication/presentation/provider/useAuth')

function Probe() {
  const { status } = useAuth()
  return <span data-testid="status">{status}</span>
}

function deferred() {
  let resolve, reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

beforeEach(() => {
  clearTokens()
  vi.clearAllMocks()
})

describe('retour OAuth, sonde de session concurrente', () => {
  it('ne supprime pas les jetons frais quand la sonde perimee echoue apres l echange', async () => {
    storeTokens({ access_token: 'perime', refresh_token: 'perime-r' })

    const probe = deferred()
    fetchCurrentUser.mockReturnValueOnce(probe.promise)

    render(<AuthProvider><Probe /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('loading'))

    // l'echange aboutit pendant que la sonde est encore en vol
    storeTokens({ access_token: 'frais', refresh_token: 'frais-r' })

    // puis la sonde perimee retombe en 401
    probe.reject(new ApiError(401, null, 'unauthorized'))
    await waitFor(() => expect(fetchCurrentUser).toHaveBeenCalled())

    expect(getAccessToken()).toBe('frais')
  })

  it('supprime bien les jetons quand rien ne les a remplaces', async () => {
    storeTokens({ access_token: 'perime', refresh_token: 'perime-r' })

    fetchCurrentUser.mockRejectedValueOnce(new ApiError(401, null, 'unauthorized'))

    render(<AuthProvider><Probe /></AuthProvider>)

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('anonymous'))
    expect(getAccessToken()).toBeNull()
  })
})
