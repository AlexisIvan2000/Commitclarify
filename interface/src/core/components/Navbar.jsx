import { useLocation, useNavigate } from 'react-router-dom'
import { GitFork, History } from 'lucide-react'
import useTranslation from '../translation/useTranslation'
import AvatarMenu from './AvatarMenu'

function Navbar({ user, quota, onLogout, onDeleteAccount }) {
  const navigate = useNavigate()
  const location = useLocation()
  const t = useTranslation()

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="navbar-brand">
          <img src="/assets/logo.png" alt="" className="navbar-logo" />
          <span className="navbar-title">Commit<span className="highlight">clarify</span></span>
        </div>

        <div className="navbar-links">
          <button
            className={`navbar-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
            onClick={() => navigate('/dashboard')}
          >
            <GitFork size={16} /> <span className="navbar-link-text">{t.actions.repos}</span>
          </button>
          <button
            className={`navbar-link ${location.pathname === '/history' ? 'active' : ''}`}
            onClick={() => navigate('/history')}
          >
            <History size={16} /> <span className="navbar-link-text">{t.actions.history}</span>
          </button>
        </div>

        {user && (
          <AvatarMenu
            user={user}
            quota={quota}
            onLogout={onLogout}
            onDeleteAccount={onDeleteAccount}
          />
        )}
      </div>
    </nav>
  )
}

export default Navbar
