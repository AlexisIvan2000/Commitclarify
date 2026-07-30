import Navbar from '@core/components/Navbar'
import useAuth from '@features/authentication/presentation/provider/useAuth'
import useQuota from '../provider/useQuota'

function AppNavbar() {
  const { user, signOut, removeAccount } = useAuth()
  const { quota } = useQuota()

  return (
    <Navbar
      user={user}
      quota={quota}
      onLogout={signOut}
      onDeleteAccount={removeAccount}
    />
  )
}

export default AppNavbar
