import { Link } from 'react-router-dom'
import HomeNavbar from '@core/components/HomeNavbar'
import { Icons } from '@core/design/icons'
import useTranslation from '@core/translation/useTranslation'
import GithubLoginButton from '../components/GithubLoginButton'

const FEATURE_ICONS = {
  secrets: Icons.secrets_detection,
  gitignore: Icons.gitignore_check,
  quality: Icons.quality_check,
  readme: Icons.readme_check,
}

function HomePage() {
  const t = useTranslation()

  return (
    <div className="home-page fade-in">
      <HomeNavbar />

      <section id="hero" className="home-hero">
        <div className="home-content">
          <img src="/assets/logo.png" alt="" className="home-logo" />
          <h1 className="home-title">
            Commit<span className="highlight">clarify</span>
          </h1>
          <p className="tagline">
            {t.home.tagline1}<br />
            {t.home.tagline2}
          </p>
          <div className="home-actions">
            <GithubLoginButton />
            <Link to="/demo" className="btn home-demo">
              <Icons.report size={15} variant="Linear" /> {t.demo.cta}
            </Link>
          </div>
        </div>
      </section>

      <section id="analyses" className="home-features-section">
        <h2 className="section-title">{t.home.featuresTitle}</h2>
        <div className="features-grid">
          {t.home.features.map((feature) => {
            const FeatureIcon = FEATURE_ICONS[feature.key]

            return (
              <div key={feature.key} className="feature-card">
                <div className="feature-card-header">
                  <FeatureIcon size={20} variant="Linear" />
                  <h3>{feature.title}</h3>
                </div>
                <p>{feature.text}</p>
              </div>
            )
          })}
        </div>
      </section>

      <section id="comment-ca-marche" className="how-it-works">
        <h2 className="section-title">{t.home.stepsTitle}</h2>
        <div className="steps">
          {t.home.steps.map((step, index) => (
            <div key={step.key} className="step">
              <span className="step-number">{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="home-footer">
        <span>{t.home.rights}</span>
        <div className="footer-links">
          <Link to="/privacy">{t.home.privacyLink}</Link>
          <Link to="/terms">{t.home.termsLink}</Link>
        </div>
      </footer>
    </div>
  )
}

export default HomePage
