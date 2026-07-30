import { useCallback, useRef, useState } from 'react'
import { Calendar, LogOut, Mail, Trash2, Zap } from 'lucide-react'
import useTranslation from '../translation/useTranslation'
import { formatMonthYear } from '../utils/date'
import useClickOutside from '../utils/useClickOutside'
import LanguageSwitch from './LanguageSwitch'

function AvatarMenu({ user, quota, onLogout, onDeleteAccount }) {
  const t = useTranslation()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const ref = useRef(null)

  useClickOutside(ref, useCallback(() => setOpen(false), []))

  async function handleDeleteAccount() {
    if (!window.confirm(t.auth.confirmDeleteAccount)) return

    setError(null)
    setDeleting(true)
    try {
      await onDeleteAccount()
    } catch (caught) {
      setError(caught.message || t.errors.deleteAccountFailed)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="avatar-menu" ref={ref}>
      <button
        className="avatar-btn"
        onClick={() => setOpen(!open)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={user.login}
      >
        <img src={user.avatar_url} alt="" className="dash-avatar" />
      </button>

      {open && (
        <div className="dropdown" role="menu">
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
              <span>{t.auth.memberSince} {formatMonthYear(user.created_at)}</span>
            </div>
            {quota && (
              <div className="dropdown-item">
                <Zap size={14} />
                <span>{quota.remaining}/{quota.limit} {t.auth.quotaRemaining}</span>
              </div>
            )}
          </div>

          <div className="dropdown-divider" />

          <div className="dropdown-language">
            <LanguageSwitch label={t.auth.interfaceLanguage} />
          </div>

          <div className="dropdown-divider" />

          <button className="dropdown-logout" onClick={onLogout}>
            <LogOut size={14} />
            {t.actions.logout}
          </button>
          <button className="dropdown-delete-account" onClick={handleDeleteAccount} disabled={deleting}>
            <Trash2 size={14} />
            {t.actions.deleteAccount}
          </button>

          {error && <p className="dropdown-error" role="alert">{error}</p>}
        </div>
      )}
    </div>
  )
}

export default AvatarMenu
