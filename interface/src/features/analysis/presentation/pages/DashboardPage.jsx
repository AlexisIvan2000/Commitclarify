import { useMemo, useState } from 'react'
import ErrorState from '@core/components/ErrorState'
import PageHeader from '@core/components/PageHeader'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import RepoCard from '../components/RepoCard'
import RepoFilters from '../components/RepoFilters'
import useReportLanguage from '../provider/useReportLanguage'
import useRepos from '../provider/useRepos'

function DashboardPage() {
  const t = useTranslation()
  const { repos, loading, error, reload } = useRepos()
  const { reportLanguage } = useReportLanguage()
  const [visibility, setVisibility] = useState(null)
  const [activeLanguage, setActiveLanguage] = useState(null)
  const [search, setSearch] = useState('')

  const languages = useMemo(
    () => [...new Set(repos.map(repo => repo.language).filter(Boolean))].sort(),
    [repos],
  )

  const filteredRepos = useMemo(() => {
    const needle = search.trim().toLowerCase()

    return repos.filter((repo) => {
      if (visibility && repo.visibility !== visibility) return false
      if (activeLanguage && repo.language !== activeLanguage) return false
      if (needle && !repo.name.toLowerCase().includes(needle)) return false
      return true
    })
  }, [repos, visibility, activeLanguage, search])

  return (
    <>
      <PageHeader
        icon={<Icons.repos size={22} variant="Linear" />}
        title={t.analysis.reposTitle}
        count={filteredRepos.length}
      />

      {loading && <Spinner />}

      {!loading && error && (
        <ErrorState message={error || t.errors.reposFailed} onRetry={reload} />
      )}

      {!loading && !error && (
        <>
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
              <RepoCard key={repo.id} repo={repo} reportLanguage={reportLanguage} />
            ))}
          </div>

          {filteredRepos.length === 0 && (
            <p className="no-results">
              {repos.length === 0 ? t.analysis.reposEmpty : t.analysis.reposNoMatch}
            </p>
          )}
        </>
      )}
    </>
  )
}

export default DashboardPage
