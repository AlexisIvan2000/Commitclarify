const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export function getToken() {
  return localStorage.getItem('access_token')
}

export function getRefreshToken() {
  return localStorage.getItem('refresh_token')
}

export function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export async function apiFetch(path, options = {}) {
  let token = getToken()
  let res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  // Si 401, tenter un refresh avant d'abandonner
  if (res.status === 401 && path !== '/auth/refresh') {
    const refreshed = await tryRefreshToken()
    if (refreshed) {
      token = getToken()
      res = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })
    }
  }

  if (!res.ok) {
    let msg = res.statusText
    try {
      const body = await res.json()
      if (body.detail) msg = body.detail
    } catch { /* pas de JSON */ }
    throw new Error(msg)
  }
  return res.json()
}

async function tryRefreshToken() {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) return false

    const data = await res.json()
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return true
  } catch {
    return false
  }
}

export function getLoginUrl() {
  return `${API_URL}/auth/github/login`
}

export async function startAnalysis(repoFullName) {
  return apiFetch(`/analyze/${repoFullName}`, { method: 'POST' })
}

export function streamAnalysis(analysisId) {
  const token = getToken()
  const url = `${API_URL}/analyze/${analysisId}/stream`
  return fetchSSE(url, token)
}

async function* fetchSSE(url, token) {
  const res = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` },
  })

  if (!res.ok) throw new Error(res.statusText)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6))
        } catch { /* ignore malformed JSON */ }
      }
    }
  }
}

export async function getAnalysisHistory() {
  return apiFetch('/analyze/history')
}

export async function getAnalysisDetail(analysisId) {
  return apiFetch(`/analyze/${analysisId}`)
}

export async function deleteAnalysis(analysisId) {
  return apiFetch(`/analyze/${analysisId}`, { method: 'DELETE' })
}

export async function deleteAllAnalyses() {
  return apiFetch('/analyze/history/all', { method: 'DELETE' })
}

export async function deleteAccount() {
  return apiFetch('/auth/account', { method: 'DELETE' })
}

export async function getQuota() {
  return apiFetch('/analyze/quota')
}

export function getExportPdfUrl(analysisId) {
  return `${API_URL}/analyze/${analysisId}/export/pdf`
}

export function getExportJsonUrl(analysisId) {
  return `${API_URL}/analyze/${analysisId}/export/json`
}

export async function downloadExport(url) {
  const token = getToken()
  const res = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(res.statusText)

  const disposition = res.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="(.+)"/)
  const filename = match ? match[1] : 'export'

  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
