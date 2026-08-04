import { useNavigate } from 'react-router-dom'
import { Icons } from '../design/icons'
import useTranslation from '../translation/useTranslation'

function NotFoundPage() {
  const navigate = useNavigate()
  const t = useTranslation()

  return (
    <div className="not-found fade-in">
      <span className="not-found-code">404</span>
      <h1 className="not-found-title">{t.notFound.title}</h1>
      <p className="not-found-text">{t.notFound.text}</p>
      <button className="btn btn-primary" onClick={() => navigate('/')}>
        <Icons.back size={16} variant="Linear" /> {t.actions.backHome}
      </button>
    </div>
  )
}

export default NotFoundPage
