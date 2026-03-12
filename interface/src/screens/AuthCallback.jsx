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

    if (accessToken && refreshToken) {
      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('refresh_token', refreshToken)

      apiFetch('/auth/me')
        .then(user => {
          onLogin(user)
          navigate('/dashboard')
        })
        .catch(() => navigate('/'))
    } else {
      navigate('/')
    }
  }, [searchParams, navigate, onLogin])

  return <Spinner text="Connexion en cours..." />
}

export default AuthCallback
