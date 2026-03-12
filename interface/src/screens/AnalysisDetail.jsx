import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ShieldAlert, FolderGit2, SearchCode, FileText,
  CheckCircle, AlertTriangle, XCircle, ArrowLeft,
  FileDown, FileJson,
} from 'lucide-react'
import { getAnalysisDetail, getToken, downloadExport, getExportPdfUrl, getExportJsonUrl } from '../services/api'
import Navbar from '../components/Navbar'
import Spinner from '../components/Spinner'

const STEP_ICONS = {
  secrets_detection: ShieldAlert,
  gitignore_check: FolderGit2,
  quality_check: SearchCode,
  readme_check: FileText,
}

const STEP_LABELS = {
  secrets_detection: 'Detection de secrets',
  gitignore_check: 'Verification .gitignore',
  quality_check: 'Qualite du code',
  readme_check: 'README vs Code',
}

const STATUS_ICONS = {
  clean: CheckCircle,
  warning: AlertTriangle,
  alert: XCircle,
}

const STATUS_COLORS = {
  clean: '#2ecc71',
  warning: '#e7a33e',
  alert: '#e74c3c',
}

function AnalysisDetail({ user, onLogout }) {
  const { analysisId } = useParams()
  const navigate = useNavigate()
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!getToken()) {
      navigate('/')
      return
    }
    loadAnalysis()
  }, [analysisId])

  async function loadAnalysis() {
    try {
      const data = await getAnalysisDetail(analysisId)
      setAnalysis(data)
    } catch {
      setError('Analyse introuvable')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <Spinner />

  if (error) {
    return (
      <div className="dash fade-in">
        <Navbar user={user} onLogout={onLogout} />
        <main className="dash-main">
          <button className="back-btn" onClick={() => navigate('/history')}>
            <ArrowLeft size={16} /> Retour
          </button>
          <div className="analysis-error">
            <XCircle size={20} />
            <span>{error}</span>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="dash fade-in">
      <Navbar user={user} onLogout={onLogout} />

      <main className="dash-main">
        <button className="back-btn" onClick={() => navigate('/history')}>
          <ArrowLeft size={16} /> Retour
        </button>

        <div className="analysis-header">
          <h2 className="analysis-title">
            Rapport : <span className="highlight">{analysis.repo_name}</span>
          </h2>
          <span className="analysis-date">
            {new Date(analysis.created_at).toLocaleDateString('fr-FR', {
              day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
            })}
          </span>
        </div>

        <div className="export-actions">
          <button className="repo-action-btn" onClick={() => downloadExport(getExportPdfUrl(analysisId))}>
            <FileDown size={14} /> Export PDF
          </button>
          <button className="repo-action-btn" onClick={() => downloadExport(getExportJsonUrl(analysisId))}>
            <FileJson size={14} /> Export JSON
          </button>
        </div>

        <div className="analysis-results-grid">
          {analysis.results.map(result => {
            const Icon = STEP_ICONS[result.aspect] || ShieldAlert
            const StatusIcon = STATUS_ICONS[result.status] || CheckCircle

            return (
              <div key={result.id} className={`analysis-result-card ${result.status}`}>
                <div className="result-card-header">
                  <Icon size={20} />
                  <h3>{STEP_LABELS[result.aspect] || result.aspect}</h3>
                  <StatusIcon size={18} style={{ color: STATUS_COLORS[result.status], marginLeft: 'auto' }} />
                </div>

                <div className="result-card-body">
                  {result.issues && result.issues.length > 0 && (
                    <div className="result-section">
                      <h4>Problemes ({result.issues.length})</h4>
                      <ul>
                        {result.issues.map((issue, i) => (
                          <li key={i} className="result-issue">
                            {typeof issue === 'string' ? issue : (
                              <>
                                <span>{issue.title || issue.message || issue.description || JSON.stringify(issue)}</span>
                                {issue.file_path && <span className="issue-file">{issue.file_path}</span>}
                                {issue.code_hint && <code className="issue-code-hint">{issue.code_hint}</code>}
                              </>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {result.recommendations && result.recommendations.length > 0 && (
                    <div className="result-section">
                      <h4>Recommandations</h4>
                      <ul>
                        {result.recommendations.map((rec, i) => (
                          <li key={i} className="result-rec">
                            {typeof rec === 'string' ? rec : rec.message || rec.description || JSON.stringify(rec)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {(!result.issues || result.issues.length === 0) && (!result.recommendations || result.recommendations.length === 0) && (
                    <p className="result-clean">Aucun probleme detecte.</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </main>
    </div>
  )
}

export default AnalysisDetail
