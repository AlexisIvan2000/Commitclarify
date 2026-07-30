import { RotateCw, XCircle } from 'lucide-react'
import useTranslation from '../translation/useTranslation'

function ErrorState({ message, onRetry }) {
  const t = useTranslation()

  return (
    <div className="analysis-error" role="alert">
      <XCircle size={20} />
      <span>{message || t.errors.unexpected}</span>
      {onRetry && (
        <button className="repo-action-btn" onClick={onRetry}>
          <RotateCw size={14} /> {t.actions.retry}
        </button>
      )}
    </div>
  )
}

export default ErrorState
