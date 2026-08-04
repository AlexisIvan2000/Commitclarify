import { Outlet } from 'react-router-dom'
import Sidebar from '@core/components/Sidebar'
import useQuota from '@features/scan/presentation/provider/useQuota'

function AppShell() {
  const { quota } = useQuota()

  return (
    <div className="app-shell">
      <Sidebar quota={quota} />
      <main className="app-content fade-in">
        <Outlet />
      </main>
    </div>
  )
}

export default AppShell
