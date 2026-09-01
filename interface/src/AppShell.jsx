import { Outlet } from 'react-router-dom'
import Sidebar from '@core/components/Sidebar'
import RunNotice from '@features/scan/presentation/components/RunNotice'
import RunsProvider from '@features/scan/presentation/provider/RunsProvider'
import useQuota from '@features/scan/presentation/provider/useQuota'
import useAuth from '@features/authentication/presentation/provider/useAuth'

function AppShell() {
  const { quota } = useQuota()
  const { user, signOut } = useAuth()

  return (
    <RunsProvider>
      <div className="app-shell">
        <Sidebar user={user} quota={quota} onLogout={signOut} />
        <main className="app-content fade-in">
          <Outlet />
        </main>
        <RunNotice />
      </div>
    </RunsProvider>
  )
}

export default AppShell
