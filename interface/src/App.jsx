import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import ErrorBoundary from '@core/components/ErrorBoundary'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import NotFoundPage from '@core/pages/NotFoundPage'
import PrivacyPage from '@core/pages/PrivacyPage'
import TermsPage from '@core/pages/TermsPage'
import LanguageProvider from '@core/translation/LanguageProvider'
import AuthProvider from '@features/authentication/presentation/provider/AuthProvider'
import useAuth from '@features/authentication/presentation/provider/useAuth'
import AuthCallbackPage from '@features/authentication/presentation/pages/AuthCallbackPage'
import HomePage from '@features/authentication/presentation/pages/HomePage'
import { SESSION_STATUS } from '@features/authentication/domain/session'
import QuotaProvider from '@features/analysis/presentation/provider/QuotaProvider'
import AnalysisDetailPage from '@features/analysis/presentation/pages/AnalysisDetailPage'
import AnalysisStreamPage from '@features/analysis/presentation/pages/AnalysisStreamPage'
import DashboardPage from '@features/analysis/presentation/pages/DashboardPage'
import HistoryPage from '@features/analysis/presentation/pages/HistoryPage'
import './App.css'

function SessionGate({ children }) {
  const { status, error, retry } = useAuth()

  if (status === SESSION_STATUS.loading) return <Spinner />
  if (status === SESSION_STATUS.unavailable) {
    return (
      <div className="dash-main">
        <ErrorState message={error} onRetry={retry} />
      </div>
    )
  }
  if (status !== SESSION_STATUS.authenticated) return <Navigate to="/" replace />

  return children
}

function LandingRoute() {
  const { status } = useAuth()

  if (status === SESSION_STATUS.loading) return <Spinner />
  if (status === SESSION_STATUS.authenticated) return <Navigate to="/dashboard" replace />

  return <HomePage />
}

function AppRoutes() {
  const location = useLocation()
  const { status } = useAuth()

  return (
    <QuotaProvider enabled={status === SESSION_STATUS.authenticated}>
      <ErrorBoundary key={location.pathname}>
        <Routes>
          <Route path="/" element={<LandingRoute />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/dashboard" element={<SessionGate><DashboardPage /></SessionGate>} />
          <Route
            path="/analyze/:owner/:repo"
            element={<SessionGate><AnalysisStreamPage /></SessionGate>}
          />
          <Route
            path="/analysis/:analysisId"
            element={<SessionGate><AnalysisDetailPage /></SessionGate>}
          />
          <Route path="/history" element={<SessionGate><HistoryPage /></SessionGate>} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ErrorBoundary>
    </QuotaProvider>
  )
}

function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </LanguageProvider>
  )
}

export default App
