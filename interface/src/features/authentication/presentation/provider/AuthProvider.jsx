import { useCallback, useEffect, useMemo, useState } from 'react'
import { messageOf } from '@core/network/errors'
import { clearTokens, getAccessToken, getRefreshToken, hasSession } from '@core/network/tokenStorage'
import { deleteAccount, fetchCurrentUser, revokeSession } from '../../data/authApi'
import { SESSION_STATUS, shouldEndSession } from '../../domain/session'
import { AuthContext } from './authContext'

function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(
    hasSession() ? SESSION_STATUS.loading : SESSION_STATUS.anonymous,
  )
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  const endSession = useCallback(() => {
    clearTokens()
    setUser(null)
    setError(null)
    setStatus(SESSION_STATUS.anonymous)
  }, [])

  useEffect(() => {
    const probed = getAccessToken()
    if (!probed) return undefined

    let cancelled = false
    const stillProbedSession = () => !cancelled && getAccessToken() === probed

    fetchCurrentUser()
      .then((currentUser) => {
        if (cancelled) return
        setUser(currentUser)
        setError(null)
        setStatus(SESSION_STATUS.authenticated)
      })
      .catch((caught) => {
        if (!stillProbedSession()) return
        if (shouldEndSession(caught)) {
          endSession()
          return
        }
        setError(messageOf(caught))
        setStatus(SESSION_STATUS.unavailable)
      })

    return () => { cancelled = true }
  }, [attempt, endSession])

  const retry = useCallback(() => {
    setError(null)
    setStatus(SESSION_STATUS.loading)
    setAttempt(previous => previous + 1)
  }, [])

  const signIn = useCallback((nextUser) => {
    setUser(nextUser)
    setError(null)
    setStatus(SESSION_STATUS.authenticated)
  }, [])

  const signOut = useCallback(async () => {
    const refreshToken = getRefreshToken()
    if (refreshToken) await revokeSession(refreshToken).catch(() => {})
    endSession()
  }, [endSession])

  const removeAccount = useCallback(async () => {
    await deleteAccount()
    endSession()
  }, [endSession])

  const value = useMemo(
    () => ({ user, status, error, signIn, signOut, removeAccount, retry }),
    [user, status, error, signIn, signOut, removeAccount, retry],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthProvider
