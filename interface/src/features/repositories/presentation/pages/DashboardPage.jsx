import { useMemo, useState } from 'react'
import ErrorState from '@core/components/ErrorState'
import PageHeader from '@core/components/PageHeader'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import EmptyState from '@core/components/EmptyState'
import RepoCard from '../components/RepoCard'
import RepoFilters from '../components/RepoFilters'
import useReportLanguage from '@features/scan/presentation/provider/useReportLanguage'
import useRepos from '../provider/useRepos'
import useAnalysisHistory from '@features/history/presentation/provider/useAnalysisHistory'
import { lastScanByRepo } from '../../domain/lastScan'

function DashboardPage() {
  const t = useTranslation()
  const { repos, loading, error, reload } = useRepos()
  const { analyses } = useAnalysisHistory()
  const { reportLanguage } = useReportLanguage()
  const [visibility, setVisibility] = useState(null)
  const [activeLanguage, setActiveLanguage] = useState(null)
  const [search, setSearch] = useState('')

  const lastScans = useMemo(() => lastScanByRepo(analyses), [analyses])

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
              <RepoCard
                key={repo.id}
                repo={repo}
                reportLanguage={reportLanguage}
                lastScan={lastScans.get(repo.name)}
              />
            ))}
          </div>

          {filteredRepos.length === 0 && repos.length === 0 && (
            <EmptyState
              icon={<Icons.repos size={30} variant="Linear" />}
              title={t.analysis.reposEmptyTitle}
              text={t.analysis.reposEmptyText}
            />
          )}

          {filteredRepos.length === 0 && repos.length > 0 && (
            <EmptyState
              icon={<Icons.search size={30} variant="Linear" />}
              title={t.analysis.reposNoMatchTitle}
              text={t.analysis.reposNoMatchText.replace('{count}', repos.length)}
              action={(
                <button
                  className="btn"
                  onClick={() => { setSearch(''); setVisibility(null); setActiveLanguage(null) }}
                >
                  {t.actions.clearSearch}
                </button>
              )}
            />
          )}
        </>
      )}
    </>
  )
}

export default DashboardPage
