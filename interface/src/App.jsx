import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Home from './screens/Home'
import Dashboard from './screens/Dashboard'
import AuthCallback from './screens/AuthCallback'
import AnalysisStream from './screens/AnalysisStream'
import AnalysisDetail from './screens/AnalysisDetail'
import History from './screens/History'
import Privacy from './screens/Privacy'
import Terms from './screens/Terms'
import NotFound from './screens/NotFound'
import Spinner from './components/Spinner'
import useAuth from './hooks/useAuth'
import './App.css'

function App() {
  const { user, setUser, ready, handleLogout } = useAuth()

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
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
