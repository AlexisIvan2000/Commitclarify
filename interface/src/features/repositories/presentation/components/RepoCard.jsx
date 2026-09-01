import { useNavigate } from 'react-router-dom'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import { formatRelative } from '@core/utils/date'
import { languageColor } from '../../domain/languageColor'
import { FAILED, NEVER, RUNNING, scanState } from '../../domain/lastScan'

const VERDICT_TONE = {
  [NEVER]: 'none',
  [RUNNING]: 'running',
  [FAILED]: 'failed',
}

function RepoCard({ repo, reportLanguage, lastScan }) {
  const t = useTranslation()
  const navigate = useNavigate()

  const { state, analysis } = scanState(lastScan)
  const tone = VERDICT_TONE[state] || 'done'
  const target = `/scan?repo=${encodeURIComponent(repo.name)}&lang=${reportLanguage}`

  const verdict = state === 'scanned'
    ? t.analysis.lastScan.done.replace(
      '{when}',
      formatRelative(analysis.created_at, t.analysis.relative),
    )
    : t.analysis.lastScan[state]

  return (
    <article className="repo-card">
      <div className="repo-card-header">
        <span className="repo-name">{repo.name}</span>
        <span className={`repo-badge ${repo.visibility === 'private' ? 'private' : 'public'}`}>
          {repo.visibility === 'private'
            ? <Icons.private size={11} variant="Linear" />
            : <Icons.public size={11} variant="Linear" />}
          {repo.visibility === 'private' ? t.analysis.private : t.analysis.public}
        </span>
      </div>

      {repo.description && <p className="repo-desc">{repo.description}</p>}

      <div className="repo-card-footer">
        {repo.language && (
          <span className="repo-lang">
            <span className="repo-lang-dot" style={{ background: languageColor(repo.language) }} />
            {repo.language}
          </span>
        )}

        {repo.pushed_at && (
          <span className="repo-pushed">{formatRelative(repo.pushed_at, t.analysis.relative)}</span>
        )}

        <span className={`repo-verdict ${tone}`}>
          {state === RUNNING && <Icons.running size={11} variant="Linear" className="spinning" />}
          {tone === 'done' && <Icons.clean size={11} variant="Linear" />}
          {state === FAILED && <Icons.error size={11} variant="Linear" />}
          {verdict}
        </span>
      </div>

      <button className="btn btn-primary repo-scan" onClick={() => navigate(target)}>
        {t.actions.analyze} <Icons.forward size={13} variant="Linear" />
      </button>
    </article>
  )
}

export default RepoCard
