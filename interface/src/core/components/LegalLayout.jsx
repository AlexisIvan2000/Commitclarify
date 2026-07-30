import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import useTranslation from '../translation/useTranslation'
import HomeNavbar from './HomeNavbar'

function LegalLayout({ title, sections }) {
  const navigate = useNavigate()
  const t = useTranslation()

  return (
    <div className="page-wrapper fade-in">
      <HomeNavbar />
      <div className="legal-page">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> {t.actions.back}
        </button>

        <h1>{title}</h1>
        <p className="legal-date">{t.legal.updatedAt} {t.legal.updatedDate}</p>

        {sections.map(section => (
          <section key={section.title}>
            <h2>{section.title}</h2>
            {section.paragraphs.map(paragraph => (
              <p key={paragraph}>{paragraph}</p>
            ))}
            {section.items.length > 0 && (
              <ul>
                {section.items.map(item => (
                  <li key={item.text}>
                    {item.term ? <><strong>{item.term}</strong> : {item.text}</> : item.text}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </div>
  )
}

export default LegalLayout
