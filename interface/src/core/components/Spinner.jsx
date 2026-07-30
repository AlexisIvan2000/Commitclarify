import useTranslation from '../translation/useTranslation'

function Spinner({ text }) {
  const t = useTranslation()

  return (
    <div className="dash-loading">
      <div className="spinner" />
      <p>{text || t.auth.loading}</p>
    </div>
  )
}

export default Spinner
