import { useNavigate, useLocation } from 'react-router-dom'

function HomeNavbar() {
  const navigate = useNavigate()
  const location = useLocation()

  function handleAnchor(hash) {
    if (location.pathname === '/') {
      document.querySelector(hash)?.scrollIntoView({ behavior: 'smooth' })
    } else {
      navigate('/' + hash)
    }
  }

  return (
    <nav className="home-navbar">
      <div className="home-navbar-inner">
        <div className="home-navbar-brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <img src="/assets/logo.png" alt="CommitClarify" className="navbar-logo" />
          <span className="navbar-title">Commit<span className="highlight">clarify</span></span>
        </div>
        <div className="home-navbar-links">
          <button onClick={() => handleAnchor('#analyses')}>Analyses</button>
          <button onClick={() => handleAnchor('#comment-ca-marche')}>Comment ca marche</button>
        </div>
      </div>
    </nav>
  )
}

export default HomeNavbar
