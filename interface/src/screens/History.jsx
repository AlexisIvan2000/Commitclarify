import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  History as HistoryIcon, Trash2, Eye, ArrowLeft,
  CheckCircle, Loader, XCircle, Clock,
} from 'lucide-react'
import { getAnalysisHistory, deleteAnalysis, deleteAllAnalyses, getToken } from '../services/api'
import Navbar from '../components/Navbar'
import Spinner from '../components/Spinner'

const STATUS_CONFIG = {
  completed: { icon: CheckCircle, color: '#2ecc71', label: 'Terminee' },
  processing: { icon: Loader, color: '#e7a33e', label: 'En cours' },
  pending: { icon: Clock, color: '#888', label: 'En attente' },
  failed: { icon: XCircle, color: '#e74c3c', label: 'Echouee' },
}

function History({ user, onLogout }) {
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const loadHistory = useCallback(async () => {
    try {
      const data = await getAnalysisHistory()
      setAnalyses(data)
    } catch {
      // silencieux
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!getToken()) {
      navigate('/')
      return
    }
    loadHistory()
  }, [navigate, loadHistory])

  async function handleDelete(id) {
    try {
      await deleteAnalysis(id)
      setAnalyses(prev => prev.filter(a => a.id !== id))
    } catch {
      // silencieux
    }
  }

  async function handleDeleteAll() {
    if (!window.confirm('Supprimer tout l\'historique ?')) return
    try {
      await deleteAllAnalyses()
      setAnalyses([])
    } catch {
      // silencieux
    }
  }

  if (loading) return <Spinner />

  return (
    <div className="dash fade-in">
      <Navbar user={user} onLogout={onLogout} />

      <main className="dash-main">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Retour
        </button>

        <div className="dash-section-header">
          <h2 className="dash-section-title">
            <HistoryIcon size={22} />
            Historique des analyses ({analyses.length})
          </h2>
          {analyses.length > 0 && (
            <button className="repo-action-btn danger" onClick={handleDeleteAll}>
              <Trash2 size={14} /> Tout supprimer
            </button>
          )}
        </div>

        {analyses.length === 0 ? (
          <p className="no-results">Aucune analyse effectuee.</p>
        ) : (
          <div className="history-list">
            {analyses.map(analysis => {
              const config = STATUS_CONFIG[analysis.status] || STATUS_CONFIG.pending
              const StatusIcon = config.icon

              return (
                <div key={analysis.id} className="history-item">
                  <div className="history-item-left">
                    <StatusIcon
                      size={18}
                      style={{ color: config.color, flexShrink: 0 }}
                      className={analysis.status === 'processing' ? 'spinning' : ''}
                    />
                    <div className="history-item-info">
                      <span className="history-repo">{analysis.repo_name}</span>
                      <span className="history-meta">
                        {config.label} &middot; {new Date(analysis.created_at).toLocaleDateString('fr-FR', {
                          day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                      </span>
                    </div>
                  </div>
                  <div className="history-item-actions">
                    {analysis.status === 'completed' && (
                      <button
                        className="repo-action-btn"
                        onClick={() => navigate(`/analysis/${analysis.id}`)}
                      >
                        <Eye size={14} /> Voir
                      </button>
                    )}
                    <button
                      className="repo-action-btn danger"
                      onClick={() => handleDelete(analysis.id)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}

export default History
