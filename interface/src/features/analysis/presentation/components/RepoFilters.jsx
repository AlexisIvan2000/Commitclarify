import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'

function RepoFilters({
  visibility, onVisibilityChange,
  languages, activeLanguage, onLanguageChange,
  search, onSearchChange,
}) {
  const t = useTranslation()

  return (
    <div className="repo-filters">
      <div className="filter-groups">
        <div className="filter-group">
          <span className="filter-label">{t.analysis.visibility}</span>
          <div className="filter-tabs">
            <button
              className={`filter-tab ${visibility === null ? 'active' : ''}`}
              onClick={() => onVisibilityChange(null)}
            >
              {t.actions.all}
            </button>
            <button
              className={`filter-tab ${visibility === 'public' ? 'active' : ''}`}
              onClick={() => onVisibilityChange('public')}
            >
              <Icons.public size={13} variant="Linear" /> {t.analysis.public}
            </button>
            <button
              className={`filter-tab ${visibility === 'private' ? 'active' : ''}`}
              onClick={() => onVisibilityChange('private')}
            >
              <Icons.private size={13} variant="Linear" /> {t.analysis.private}
            </button>
          </div>
        </div>

        {languages.length > 0 && (
          <div className="filter-group">
            <span className="filter-label">{t.analysis.language}</span>
            <div className="filter-tabs">
              <button
                className={`filter-tab ${activeLanguage === null ? 'active' : ''}`}
                onClick={() => onLanguageChange(null)}
              >
                {t.actions.all}
              </button>
              {languages.map(language => (
                <button
                  key={language}
                  className={`filter-tab ${activeLanguage === language ? 'active' : ''}`}
                  onClick={() => onLanguageChange(language)}
                >
                  {language}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="filter-search">
        <Icons.search size={16} variant="Linear" />
        <input
          type="text"
          placeholder={t.actions.search}
          aria-label={t.actions.search}
          value={search}
          onChange={event => onSearchChange(event.target.value)}
        />
      </div>
    </div>
  )
}

export default RepoFilters
