import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
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
      <div className="callback-error fade-in">
        <ErrorState message={error} />
        <button className="btn btn-primary" onClick={() => navigate('/', { replace: true })}>
          <Icons.back size={16} variant="Linear" /> {t.actions.backHome}
        </button>
      </div>
    )
  }

  return <Spinner text={t.auth.loggingIn} />
}

export default AuthCallbackPage
