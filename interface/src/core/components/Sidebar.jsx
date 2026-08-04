import { NavLink } from 'react-router-dom'
import useTranslation from '@core/translation/useTranslation'
import { Icons } from '@core/design/icons'

const NAV_ITEMS = [
  { key: 'repos', to: '/dashboard', Icon: Icons.repos },
  { key: 'scan', to: '/scan', Icon: Icons.scan },
  { key: 'report', to: '/report', Icon: Icons.report },
  { key: 'history', to: '/history', Icon: Icons.history },
  { key: 'account', to: '/account', Icon: Icons.account },
]

function Sidebar({ quota }) {
  const t = useTranslation()

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="/assets/logo.png" alt="CommitClarify" />
        <div>
          <span className="sidebar-brand-name">CommitClarify</span>
          <span className="sidebar-brand-tag">{t.nav.freeScan}</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(item => {
          const ItemIcon = item.Icon

          return (
            <NavLink
              key={item.key}
              to={item.to}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <ItemIcon size={18} variant="Linear" />
              <span>{t.nav[item.key]}</span>
            </NavLink>
          )
        })}
      </nav>

      {Number.isInteger(quota?.remaining) && (
        <div className="sidebar-quota">
          <span className="sidebar-quota-value">{quota.remaining}</span>
          <span className="sidebar-quota-label">{t.nav.triagesLeft}</span>
        </div>
      )}
    </aside>
  )
}

export default Sidebar
