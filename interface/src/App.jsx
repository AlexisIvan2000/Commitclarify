import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Home from './screens/Home'
import Dashboard from './screens/Dashboard'
import AuthCallback from './screens/AuthCallback'
import AnalysisStream from './screens/AnalysisStream'
import AnalysisDetail from './screens/AnalysisDetail'
import History from './screens/History'
import Privacy from './screens/Privacy'
import Terms from './screens/Terms'
import Spinner from './components/Spinner'
import { apiFetch, getToken, getRefreshToken, clearTokens } from './services/api'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = getToken()
    console.log('[App] useEffect — token:', token ? 'present' : 'absent')

    if (!token) {
      console.log('[App] No token, setting ready')
      setReady(true)
      return
    }

    console.log('[App] Fetching /auth/me...')
    apiFetch('/auth/me')
      .then(u => {
        console.log('[App] /auth/me OK:', u?.login)
        setUser(u)
      })
      .catch(err => {
        console.error('[App] /auth/me FAILED:', err.message)
        clearTokens()
      })
      .finally(() => {
        console.log('[App] Setting ready=true')
        setReady(true)
      })
  }, [])

  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: getRefreshToken() }),
      })
    } catch { /* silent */ }
    clearTokens()
    setUser(null)
  }

  if (!ready) return <Spinner text="Chargement..." />

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={user ? <Navigate to="/dashboard" /> : <Home />} />
        <Route path="/auth/callback" element={<AuthCallback onLogin={setUser} />} />
        <Route path="/dashboard" element={
          user ? <Dashboard user={user} onLogout={handleLogout} /> : <Navigate to="/" />
        } />
        <Route path="/analyze/:owner/:repo" element={
          user ? <AnalysisStream user={user} onLogout={handleLogout} /> : <Navigate to="/" />
        } />
        <Route path="/analysis/:analysisId" element={
          user ? <AnalysisDetail user={user} onLogout={handleLogout} /> : <Navigate to="/" />
        } />
        <Route path="/history" element={
          user ? <History user={user} onLogout={handleLogout} /> : <Navigate to="/" />
        } />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
