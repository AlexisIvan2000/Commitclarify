import { BrowserRouter, Navigate, Route, Routes, useLocation, useParams, useSearchParams } from 'react-router-dom'
import ErrorBoundary from '@core/components/ErrorBoundary'
import ErrorState from '@core/components/ErrorState'
import Spinner from '@core/components/Spinner'
import NotFoundPage from '@core/pages/NotFoundPage'
import PrivacyPage from '@core/pages/PrivacyPage'
import TermsPage from '@core/pages/TermsPage'
import LanguageProvider from '@core/translation/LanguageProvider'
import AuthProvider from '@features/authentication/presentation/provider/AuthProvider'
import useAuth from '@features/authentication/presentation/provider/useAuth'
import AccountPage from '@features/authentication/presentation/pages/AccountPage'
import AuthCallbackPage from '@features/authentication/presentation/pages/AuthCallbackPage'
import HomePage from '@features/authentication/presentation/pages/HomePage'
import { SESSION_STATUS } from '@features/authentication/domain/session'
import QuotaProvider from '@features/analysis/presentation/provider/QuotaProvider'
import DashboardPage from '@features/analysis/presentation/pages/DashboardPage'
import HistoryPage from '@features/analysis/presentation/pages/HistoryPage'
import LatestReportPage from '@features/analysis/presentation/pages/LatestReportPage'
import ReportPage from '@features/analysis/presentation/pages/ReportPage'
import ScanPage from '@features/analysis/presentation/pages/ScanPage'
import AppShell from './AppShell'
import './App.css'

function SessionGate({ children }) {
  const { status, error, retry } = useAuth()

  if (status === SESSION_STATUS.loading) return <Spinner />
  if (status === SESSION_STATUS.unavailable) {
    return (
      <div className="app-content">
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

function LegacyScanRoute() {
  const { owner, repo } = useParams()
  const [searchParams] = useSearchParams()
  const language = searchParams.get('lang')
  const query = `repo=${encodeURIComponent(`${owner}/${repo}`)}${language ? `&lang=${language}` : ''}`

  return <Navigate to={`/scan?${query}`} replace />
}

function LegacyReportRoute() {
  const { analysisId } = useParams()

  return <Navigate to={`/report/${analysisId}`} replace />
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

          <Route element={<SessionGate><AppShell /></SessionGate>}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/scan" element={<ScanPage />} />
            <Route path="/report" element={<LatestReportPage />} />
            <Route path="/report/:analysisId" element={<ReportPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/account" element={<AccountPage />} />
          </Route>

          <Route path="/analyze/:owner/:repo" element={<LegacyScanRoute />} />
          <Route path="/analysis/:analysisId" element={<LegacyReportRoute />} />

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
