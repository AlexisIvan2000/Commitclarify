import { useEffect, useState, useMemo } from 'react'
import { GitFork } from 'lucide-react'
import { apiFetch } from '../services/api'
import Navbar from '../components/Navbar'
import RepoCard from '../components/RepoCard'
import RepoFilters from '../components/RepoFilters'
import Spinner from '../components/Spinner'


function Dashboard({ user, onLogout }) {
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [visibility, setVisibility] = useState(null)
  const [activeLanguage, setActiveLanguage] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    apiFetch('/repos/')
      .then(setRepos)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const languages = useMemo(() => {
    const langs = [...new Set(repos.map(r => r.language).filter(Boolean))]
    return langs.sort()
  }, [repos])

  const filteredRepos = useMemo(() => {
    return repos.filter(repo => {
      if (visibility && repo.visibility !== visibility) return false
      if (activeLanguage && repo.language !== activeLanguage) return false
      if (search && !repo.name.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [repos, visibility, activeLanguage, search])

  if (loading) return <Spinner />

  return (
    <div className="dash fade-in">
      <Navbar user={user} onLogout={onLogout} />

      <main className="dash-main">
        <div className="dash-section-header">
          <h2 className="dash-section-title">
            <GitFork size={22} />
            Vos repositories ({filteredRepos.length})
          </h2>
        </div>

        <RepoFilters
          visibility={visibility}
          onVisibilityChange={setVisibility}
          languages={languages}
          activeLanguage={activeLanguage}
          onLanguageChange={setActiveLanguage}
          search={search}
          onSearchChange={setSearch}
        />

        <div className="repo-grid">
          {filteredRepos.map(repo => (
            <RepoCard key={repo.id} repo={repo} />
          ))}
        </div>

        {filteredRepos.length === 0 && (
          <p className="no-results">Aucun repository trouve.</p>
        )}
      </main>
    </div>
  )
}

export default Dashboard
