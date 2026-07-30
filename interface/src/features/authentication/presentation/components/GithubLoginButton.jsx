import useTranslation from '@core/translation/useTranslation'
import { getLoginUrl } from '../../data/authApi'

function GithubLoginButton() {
  const t = useTranslation()
  return (
    <button className="github-btn" onClick={() => { window.location.href = getLoginUrl() }}>
      <img src="/assets/github-logo.svg" alt="" width="20" height="20" />
      {t.auth.continueWithGithub}
    </button>
  )
}

export default GithubLoginButton
