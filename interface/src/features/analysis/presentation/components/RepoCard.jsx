import { useNavigate } from 'react-router-dom'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'

function RepoCard({ repo, reportLanguage }) {
  const t = useTranslation()
  const navigate = useNavigate()

  const target = `/scan?repo=${encodeURIComponent(repo.name)}&lang=${reportLanguage}`

  return (
    <div className="repo-card">
      <div className="repo-card-header">
        <span className="repo-name">{repo.name}</span>
        {repo.visibility === 'private' ? (
          <span className="repo-badge private">
            <Icons.private size={12} variant="Linear" /> {t.analysis.private}
          </span>
        ) : (
          <span className="repo-badge public">
            <Icons.public size={12} variant="Linear" /> {t.analysis.public}
          </span>
        )}
      </div>

      {repo.description && <p className="repo-desc">{repo.description}</p>}

      <div className="repo-card-footer">
        {repo.language && <span className="repo-lang">{repo.language}</span>}
        <div className="repo-actions">
          <button className="btn btn-primary" onClick={() => navigate(target)}>
            {t.actions.analyze} <Icons.forward size={14} variant="Linear" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default RepoCard
