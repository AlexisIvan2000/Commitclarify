import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiFetch } from '../services/api'
import Spinner from '../components/Spinner'

function AuthCallback({ onLogin }) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const accessToken = searchParams.get('access_token')
    const refreshToken = searchParams.get('refresh_token')
    console.log('[AuthCallback] tokens from URL:', accessToken ? 'present' : 'MISSING', refreshToken ? 'present' : 'MISSING')

    if (accessToken && refreshToken) {
      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('refresh_token', refreshToken)
      console.log('[AuthCallback] Tokens saved, fetching /auth/me...')

      apiFetch('/auth/me')
        .then(user => {
          console.log('[AuthCallback] /auth/me OK:', user?.login, '— navigating to /dashboard')
          onLogin(user)
          navigate('/dashboard')
        })
        .catch(err => {
          console.error('[AuthCallback] /auth/me FAILED:', err.message)
          navigate('/')
        })
    } else {
      console.warn('[AuthCallback] No tokens in URL, redirecting to /')
      navigate('/')
    }
  }, [searchParams, navigate, onLogin])

  return <Spinner text="Connexion en cours..." />
}

export default AuthCallback
