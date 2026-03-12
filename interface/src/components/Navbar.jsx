import { useNavigate, useLocation } from 'react-router-dom'
import { GitFork, History } from 'lucide-react'
import AvatarMenu from './AvatarMenu'

function Navbar({ user, onLogout }) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="navbar-brand">
          <img src="/assets/logo.png" alt="CommitClarify" className="navbar-logo" />
          <span className="navbar-title">Commit<span className="highlight">clarify</span></span>
        </div>
        <div className="navbar-links">
          <button
            className={`navbar-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
            onClick={() => navigate('/dashboard')}
          >
            <GitFork size={16} /> Repos
          </button>
          <button
            className={`navbar-link ${location.pathname === '/history' ? 'active' : ''}`}
            onClick={() => navigate('/history')}
          >
            <History size={16} /> Historique
          </button>
        </div>
        {user && <AvatarMenu user={user} onLogout={onLogout} />}
      </div>
    </nav>
  )
}

export default Navbar
