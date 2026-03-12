import { Search, Globe, Lock } from 'lucide-react'

function RepoFilters({
  visibility, onVisibilityChange,
  languages, activeLanguage, onLanguageChange,
  search, onSearchChange,
}) {
  return (
    <div className="repo-filters">
      <div className="filter-groups">
        <div className="filter-group">
          <span className="filter-label">Visibilité</span>
          <div className="filter-tabs">
            <button
              className={`filter-tab ${visibility === null ? 'active' : ''}`}
              onClick={() => onVisibilityChange(null)}
            >
              Tous
            </button>
            <button
              className={`filter-tab ${visibility === 'public' ? 'active' : ''}`}
              onClick={() => onVisibilityChange('public')}
            >
              <Globe size={13} /> Public
            </button>
            <button
              className={`filter-tab ${visibility === 'private' ? 'active' : ''}`}
              onClick={() => onVisibilityChange('private')}
            >
              <Lock size={13} /> Privé
            </button>
          </div>
        </div>

        {languages.length > 0 && (
          <div className="filter-group">
            <span className="filter-label">Langage</span>
            <div className="filter-tabs">
              <button
                className={`filter-tab ${activeLanguage === null ? 'active' : ''}`}
                onClick={() => onLanguageChange(null)}
              >
                Tous
              </button>
              {languages.map(lang => (
                <button
                  key={lang}
                  className={`filter-tab ${activeLanguage === lang ? 'active' : ''}`}
                  onClick={() => onLanguageChange(lang)}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="filter-search">
        <Search size={16} />
        <input
          type="text"
          placeholder="Rechercher..."
          value={search}
          onChange={e => onSearchChange(e.target.value)}
        />
      </div>
    </div>
  )
}

export default RepoFilters
