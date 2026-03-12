import { useEffect, useState } from 'react'
import { apiFetch, getToken, getRefreshToken, clearTokens } from '../services/api'

export default function useAuth() {
  const hasToken = !!getToken()
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!hasToken)

  useEffect(() => {
    if (!hasToken) return

    apiFetch('/auth/me')
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setReady(true))
  }, [hasToken])

  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: getRefreshToken() }),
      })
    } catch { /* silent */ }
    clearTokens()
    setUser(null)
  }

  return { user, setUser, ready, handleLogout }
}
