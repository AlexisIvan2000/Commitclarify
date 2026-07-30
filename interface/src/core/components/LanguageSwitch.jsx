import { CATALOGS } from '../translation'
import { useLanguage } from '../translation/useTranslation'

function LanguageSwitch({ label, value, onChange, options, hint }) {
  const { language, available, changeLanguage } = useLanguage()

  const current = value ?? language
  const choices = options ?? available
  const apply = onChange ?? changeLanguage

  return (
    <div className="language-switch">
      {label && <span className="language-switch-label">{label}</span>}
      <div className="language-switch-options">
        {choices.map(choice => (
          <button
            key={choice}
            type="button"
            className={`filter-tab ${current === choice ? 'active' : ''}`}
            onClick={() => apply(choice)}
            aria-pressed={current === choice}
          >
            {CATALOGS[choice].languageName}
          </button>
        ))}
      </div>
      {hint && <span className="language-switch-hint">{hint}</span>}
    </div>
  )
}

export default LanguageSwitch
