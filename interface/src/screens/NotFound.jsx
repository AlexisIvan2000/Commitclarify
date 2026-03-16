import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="not-found fade-in">
      <span className="not-found-code">404</span>
      <h1 className="not-found-title">Page introuvable</h1>
      <p className="not-found-text">La page que vous cherchez n'existe pas ou a ete deplacee.</p>
      <button className="repo-action-btn primary" onClick={() => navigate('/')}>
        <ArrowLeft size={16} /> Retour a l'accueil
      </button>
    </div>
  )
}

export default NotFound
