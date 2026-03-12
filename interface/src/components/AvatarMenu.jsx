import { useState, useRef, useCallback } from 'react'
import { LogOut, Mail, Calendar, Zap, Trash2 } from 'lucide-react'
import { getQuota, deleteAccount, clearTokens } from '../services/api'
import useClickOutside from '../hooks/useClickOutside'
import { useEffect } from 'react'

function AvatarMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false)
  const [quota, setQuota] = useState(null)
  const ref = useRef(null)

  useClickOutside(ref, useCallback(() => setOpen(false), []))

  useEffect(() => {
    getQuota().then(setQuota).catch(() => {})
  }, [])

  async function handleDeleteAccount() {
    if (!window.confirm('Supprimer definitivement votre compte et toutes vos donnees ?')) return
    try {
      await deleteAccount()
      clearTokens()
      onLogout()
    } catch { /* silent */ }
  }

  return (
    <div className="avatar-menu" ref={ref}>
      <button className="avatar-btn" onClick={() => setOpen(!open)}>
        <img src={user.avatar_url} alt={user.login} className="dash-avatar" />
      </button>
      {open && (
        <div className="dropdown">
          <div className="dropdown-header">
            <div className="dropdown-info">
              <span className="dropdown-name">{user.username}</span>
              <span className="dropdown-login">@{user.login}</span>
            </div>
          </div>
          <div className="dropdown-divider" />
          <div className="dropdown-details">
            {user.email && (
              <div className="dropdown-item">
                <Mail size={14} />
                <span>{user.email}</span>
              </div>
            )}
            <div className="dropdown-item">
              <Calendar size={14} />
              <span>Membre depuis {new Date(user.created_at).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}</span>
            </div>
            {quota && (
              <div className="dropdown-item">
                <Zap size={14} />
                <span>{quota.remaining}/{quota.limit} analyses restantes aujourd'hui</span>
              </div>
            )}
          </div>
          <div className="dropdown-divider" />
          <button className="dropdown-logout" onClick={onLogout}>
            <LogOut size={14} />
            Deconnexion
          </button>
          <button className="dropdown-delete-account" onClick={handleDeleteAccount}>
            <Trash2 size={14} />
            Supprimer mon compte
          </button>
        </div>
      )}
    </div>
  )
}

export default AvatarMenu
