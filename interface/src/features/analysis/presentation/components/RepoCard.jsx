import { useNavigate } from 'react-router-dom'
import { ArrowRight, Globe, Lock } from 'lucide-react'
import useTranslation from '@core/translation/useTranslation'

function RepoCard({ repo, reportLanguage }) {
  const t = useTranslation()
  const navigate = useNavigate()

  return (
    <div className="repo-card">
      <div className="repo-card-header">
        <span className="repo-name">{repo.name}</span>
        {repo.visibility === 'private' ? (
          <span className="repo-badge private"><Lock size={12} /> {t.analysis.private}</span>
        ) : (
          <span className="repo-badge public"><Globe size={12} /> {t.analysis.public}</span>
        )}
      </div>

      {repo.description && <p className="repo-desc">{repo.description}</p>}

      <div className="repo-card-footer">
        {repo.language && <span className="repo-lang">{repo.language}</span>}
        <div className="repo-actions">
          <button
            className="repo-action-btn primary"
            onClick={() => navigate(`/analyze/${repo.name}?lang=${reportLanguage}`)}
          >
            {t.actions.analyze} <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default RepoCard
