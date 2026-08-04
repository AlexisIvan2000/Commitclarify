import { useState } from 'react'
import LanguageSwitch from '@core/components/LanguageSwitch'
import PageHeader from '@core/components/PageHeader'
import Spinner from '@core/components/Spinner'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import { formatMonthYear } from '@core/utils/date'
import useQuota from '@features/scan/presentation/provider/useQuota'
import useReportLanguage from '@features/scan/presentation/provider/useReportLanguage'
import useAuth from '../provider/useAuth'

function AccountPage() {
  const t = useTranslation()
  const { user, signOut, removeAccount } = useAuth()
  const { quota } = useQuota()
  const { reportLanguage, setReportLanguage } = useReportLanguage()
  const [error, setError] = useState(null)
  const [deleting, setDeleting] = useState(false)

  if (!user) return <Spinner />

  async function handleDeleteAccount() {
    if (!window.confirm(t.auth.confirmDeleteAccount)) return

    setError(null)
    setDeleting(true)
    try {
      await removeAccount()
    } catch (caught) {
      setError(caught.message || t.errors.deleteAccountFailed)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <PageHeader
        icon={<Icons.account size={22} variant="Linear" />}
        title={t.account.title}
      />

      <section className="account-identity">
        <img src={user.avatar_url} alt="" className="account-avatar" />
        <div>
          <span className="account-name">{user.username}</span>
          <span className="account-login">@{user.login}</span>
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title">{t.account.profile}</h2>
        <dl className="metrics-panel-list">
          {user.email && (
            <div className="metrics-row">
              <dt><Icons.mail size={14} variant="Linear" /> {t.account.email}</dt>
              <dd>{user.email}</dd>
            </div>
          )}
          <div className="metrics-row">
            <dt><Icons.calendar size={14} variant="Linear" /> {t.auth.memberSince}</dt>
            <dd>{formatMonthYear(user.created_at)}</dd>
          </div>
          {quota && (
            <div className="metrics-row">
              <dt><Icons.quota size={14} variant="Linear" /> {t.auth.quotaRemaining}</dt>
              <dd>{quota.remaining}/{quota.limit}</dd>
            </div>
          )}
        </dl>
      </section>

      <section className="panel">
        <h2 className="panel-title">{t.account.preferences}</h2>
        <LanguageSwitch label={t.auth.interfaceLanguage} />
        <LanguageSwitch
          label={t.analysis.reportLanguage}
          hint={t.analysis.reportLanguageHint}
          value={reportLanguage}
          onChange={setReportLanguage}
        />
      </section>

      <section className="panel panel-danger">
        <h2 className="panel-title">{t.account.danger}</h2>
        <p className="panel-hint">{t.account.dangerHint}</p>
        <div className="panel-actions">
          <button className="btn" onClick={signOut}>
            <Icons.logout size={14} variant="Linear" /> {t.actions.logout}
          </button>
          <button className="btn btn-danger" onClick={handleDeleteAccount} disabled={deleting}>
            <Icons.trash size={14} variant="Linear" /> {t.actions.deleteAccount}
          </button>
        </div>
        {error && <p className="panel-error" role="alert">{error}</p>}
      </section>
    </>
  )
}

export default AccountPage
