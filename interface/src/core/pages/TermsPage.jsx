import LegalLayout from '../components/LegalLayout'
import useTranslation from '../translation/useTranslation'

function TermsPage() {
  const t = useTranslation()

  return <LegalLayout title={t.legal.termsTitle} sections={t.legal.terms} />
}

export default TermsPage
