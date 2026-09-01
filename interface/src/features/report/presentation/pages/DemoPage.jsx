import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import GithubLoginButton from '@features/authentication/presentation/components/GithubLoginButton'
import { resultsByAspect } from '@features/scan/domain/report'
import AnalysisReport from '../components/AnalysisReport'

function DemoPage() {
  const t = useTranslation()
  const [fixture, setFixture] = useState(null)
  const [failed, setFailed] = useState(false)
  const [sorted, setSorted] = useState(false)

  useEffect(() => {
    let abandoned = false

    import('../../demo/reactScan.json')
      .then(module => { if (!abandoned) setFixture(module.default) })
      .catch(() => { if (!abandoned) setFailed(true) })

    return () => { abandoned = true }
  }, [])

  const analysis = fixture ? (sorted ? fixture.sorted : fixture.base) : null

  return (
    <div className="demo-page fade-in">
      <div className="demo-banner">
        <Icons.report size={16} variant="Linear" />
        <div className="demo-banner-text">
          <strong>{t.demo.title}</strong>
          <span>{sorted ? t.demo.sortedNote : t.demo.note}</span>
        </div>

        <button
          type="button"
          className={`btn ${sorted ? 'btn-quiet' : ''}`}
          onClick={() => setSorted(previous => !previous)}
        >
          <Icons.triage size={13} variant="Linear" />
          {sorted ? t.demo.showRaw : t.demo.showSorted}
        </button>

        <GithubLoginButton />
        <Link to="/" className="demo-back">{t.actions.backHome}</Link>
      </div>

      <div className="demo-body">
        {!fixture && !failed && <Spinner />}
        {failed && <ErrorState message={t.demo.failed} />}
        {analysis && (
          <AnalysisReport analysis={analysis} results={resultsByAspect(analysis)} />
        )}
      </div>
    </div>
  )
}

export default DemoPage
