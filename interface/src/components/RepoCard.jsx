import { useNavigate } from 'react-router-dom'
import { Globe, Lock, ArrowRight } from 'lucide-react'

function RepoCard({ repo }) {
  const navigate = useNavigate()

  function handleAnalyze() {
    navigate(`/analyze/${repo.name}`)
  }

  return (
    <div className="repo-card">
      <div className="repo-card-header">
        <span className="repo-name">{repo.name}</span>
        {repo.visibility === 'private' ? (
          <span className="repo-badge private"><Lock size={12} /> Prive</span>
        ) : (
          <span className="repo-badge public"><Globe size={12} /> Public</span>
        )}
      </div>
      {repo.description && (
        <p className="repo-desc">{repo.description}</p>
      )}
      <div className="repo-card-footer">
        {repo.language && (
          <span className="repo-lang">{repo.language}</span>
        )}
        <div className="repo-actions">
          <button className="repo-action-btn primary" onClick={handleAnalyze}>
            Analyser <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default RepoCard
