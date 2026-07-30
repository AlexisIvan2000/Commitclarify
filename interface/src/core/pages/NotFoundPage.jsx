import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import useTranslation from '../translation/useTranslation'

function NotFoundPage() {
  const navigate = useNavigate()
  const t = useTranslation()

  return (
    <div className="not-found fade-in">
      <span className="not-found-code">404</span>
      <h1 className="not-found-title">{t.notFound.title}</h1>
      <p className="not-found-text">{t.notFound.text}</p>
      <button className="repo-action-btn primary" onClick={() => navigate('/')}>
        <ArrowLeft size={16} /> {t.actions.backHome}
      </button>
    </div>
  )
}

export default NotFoundPage
