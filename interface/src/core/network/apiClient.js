import { getStrings } from '../translation'
import { ApiError, NetworkError } from './errors'
import { getAccessToken, getRefreshToken, storeTokens } from './tokenStorage'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let pendingRefresh = null

function buildHeaders(headers, token) {
  const merged = { ...headers }
  if (token) merged.Authorization = `Bearer ${token}`
  return merged
}

async function send(path, options, token) {
  try {
    return await fetch(`${API_URL}${path}`, {
      ...options,
      headers: buildHeaders(options.headers, token),
    })
  } catch (cause) {
    throw new NetworkError(cause)
  }
}

async function toApiError(response) {
  let detail = null
  let code = null

  try {
    const body = await response.json()
    if (typeof body?.detail === 'string' && body.detail.trim()) detail = body.detail
    if (typeof body?.code === 'string' && body.code.trim()) code = body.code
  } catch {
    detail = null
  }

  return new ApiError(response.status, detail, code)
}

async function requestRefresh() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  const response = await send('/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) return false

  return storeTokens(await response.json())
}

function refreshSession() {
  if (!pendingRefresh) {
    pendingRefresh = requestRefresh().finally(() => {
      pendingRefresh = null
    })
  }
  return pendingRefresh
}

export async function request(path, options = {}) {
  let response = await send(path, options, getAccessToken())

  if (response.status === 401 && path !== '/auth/refresh' && await refreshSession()) {
    response = await send(path, options, getAccessToken())
  }

  if (!response.ok) throw await toApiError(response)
  return response
}

export async function requestJson(path, options = {}) {
  const response = await request(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })

  if (response.status === 204) return null
  return response.json()
}

export async function requestFile(path) {
  const response = await request(path)
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="([^"]+)"/)

  return { blob: await response.blob(), filename: match?.[1] || null }
}

export async function* openEventStream(path, { signal } = {}) {
  const response = await request(path, signal ? { signal } : {})
  if (!response.body) {
    throw new ApiError(response.status, getStrings().errors.streamUnavailable, 'stream_unavailable')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          yield JSON.parse(line.slice(6))
        } catch {
          continue
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {})
  }
}
