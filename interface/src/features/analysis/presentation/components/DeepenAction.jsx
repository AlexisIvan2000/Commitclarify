import { Sparkles } from 'lucide-react'
import useTranslation from '@core/translation/useTranslation'

function DeepenAction({ remaining, running, onStart }) {
  const t = useTranslation()
  const exhausted = remaining === 0

  return (
    <div className="deepen-action">
      <button
        type="button"
        className="repo-action-btn primary"
        onClick={onStart}
        disabled={running || exhausted}
      >
        <Sparkles size={14} />
        {running ? t.analysis.deepen.running : t.analysis.deepen.label}
      </button>

      <p className="deepen-hint">{t.analysis.deepen.hint}</p>

      {Number.isInteger(remaining) && (
        <p className={`deepen-balance ${exhausted ? 'exhausted' : ''}`}>
          {exhausted
            ? t.analysis.deepen.exhausted
            : t.analysis.deepen.remaining.replace('{count}', remaining)}
        </p>
      )}
    </div>
  )
}

export default DeepenAction
