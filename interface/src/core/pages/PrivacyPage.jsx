import LegalLayout from '../components/LegalLayout'
import useTranslation from '../translation/useTranslation'

function PrivacyPage() {
  const t = useTranslation()

  return <LegalLayout title={t.legal.privacyTitle} sections={t.legal.privacy} />
}

export default PrivacyPage
