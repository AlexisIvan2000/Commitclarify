import { Icons } from '../design/icons'
import useTranslation from '../translation/useTranslation'

function ErrorState({ message, onRetry }) {
  const t = useTranslation()

  return (
    <div className="analysis-error" role="alert">
      <Icons.error size={18} variant="Linear" />
      <span>{message || t.errors.unexpected}</span>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          <Icons.retry size={14} variant="Linear" /> {t.actions.retry}
        </button>
      )}
    </div>
  )
}

export default ErrorState
