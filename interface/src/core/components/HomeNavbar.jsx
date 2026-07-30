import { useLocation, useNavigate } from 'react-router-dom'
import useTranslation from '../translation/useTranslation'
import LanguageSwitch from './LanguageSwitch'

function HomeNavbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const t = useTranslation()

  function handleAnchor(hash) {
    if (location.pathname === '/') {
      document.querySelector(hash)?.scrollIntoView({ behavior: 'smooth' })
      return
    }
    navigate('/' + hash)
  }

  return (
    <nav className="home-navbar">
      <div className="home-navbar-inner">
        <button className="home-navbar-brand" onClick={() => navigate('/')}>
          <img src="/assets/logo.png" alt="" className="navbar-logo" />
          <span className="navbar-title">Commit<span className="highlight">clarify</span></span>
        </button>
        <div className="home-navbar-links">
          <button onClick={() => handleAnchor('#analyses')}>{t.home.navAnalyses}</button>
          <button onClick={() => handleAnchor('#comment-ca-marche')}>{t.home.navHowItWorks}</button>
          <LanguageSwitch />
        </div>
      </div>
    </nav>
  )
}

export default HomeNavbar
