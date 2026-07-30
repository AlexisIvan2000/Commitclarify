import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import useTranslation from '@core/translation/useTranslation'
import { messageOf } from '@core/network/errors'
import { exchangeAuthCode, fetchCurrentUser } from '../../data/authApi'
import useAuth from '../provider/useAuth'

function AuthCallbackPage() {
  const t = useTranslation()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { signIn } = useAuth()
  const [exchangeError, setExchangeError] = useState(null)

  const code = searchParams.get('code')
  const failure = searchParams.get('error')
  const paramError = failure || !code
    ? t.auth.callbackErrors[failure] || t.errors.loginFailed
    : null
  const error = paramError || exchangeError

  useEffect(() => {
    if (!code || failure) return

    let cancelled = false

    exchangeAuthCode(code)
      .then(fetchCurrentUser)
      .then((user) => {
        if (cancelled) return
        signIn(user)
        navigate('/dashboard', { replace: true })
      })
      .catch((caught) => {
        if (!cancelled) setExchangeError(messageOf(caught))
      })

    return () => { cancelled = true }
  }, [code, failure, navigate, signIn])

  if (error) {
    return (
      <div className="dash-main fade-in">
        <ErrorState message={error} />
        <button className="repo-action-btn primary" onClick={() => navigate('/', { replace: true })}>
          <ArrowLeft size={16} /> {t.actions.backHome}
        </button>
      </div>
    )
  }

  return <Spinner text={t.auth.loggingIn} />
}

export default AuthCallbackPage
