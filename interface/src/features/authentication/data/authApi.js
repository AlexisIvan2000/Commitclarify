import { API_URL, requestJson } from '@core/network/apiClient'
import { storeTokens } from '@core/network/tokenStorage'

export function getLoginUrl() {
  return `${API_URL}/auth/github/login`
}

export async function exchangeAuthCode(code) {
  const tokens = await requestJson('/auth/exchange', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })

  storeTokens(tokens)
  return tokens
}

export function fetchCurrentUser() {
  return requestJson('/auth/me')
}

export function revokeSession(refreshToken) {
  return requestJson('/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

export function deleteAccount() {
  return requestJson('/auth/account', { method: 'DELETE' })
}
