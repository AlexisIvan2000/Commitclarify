import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiFetch, exchangeAuthCode } from '../services/api'
import Spinner from '../components/Spinner'

function AuthCallback({ onLogin }) {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const code = searchParams.get('code')
    const error = searchParams.get('error')

    if (error || !code) {
      navigate('/', { replace: true })
      return
    }

    let cancelled = false

    exchangeAuthCode(code)
      .then(() => apiFetch('/auth/me'))
      .then(user => {
        if (cancelled) return
        onLogin(user)
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        if (!cancelled) navigate('/', { replace: true })
      })

    return () => { cancelled = true }
  }, [searchParams, navigate, onLogin])

  return <Spinner text="Connexion en cours..." />
}

export default AuthCallback
