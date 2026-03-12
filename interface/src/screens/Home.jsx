import {
  ShieldAlert, FolderGit2, SearchCode, FileText,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getLoginUrl } from '../services/api'
import HomeNavbar from '../components/HomeNavbar'

function Home() {
  const handleLogin = () => {
    window.location.href = getLoginUrl()
  }

  return (
    <div className="home-page fade-in">
      <HomeNavbar />
      <section id="hero" className="home-hero">
        <div className="home-content">
          <img src="/assets/logo.png" alt="CommitClarify" className="home-logo" />
          <h1 className="home-title">
            Commit<span className="highlight">clarify</span>
          </h1>
          <p className="tagline">
            Le gardien intelligent de vos repositories.<br />
            Analysez la sécurité, la cohérence et la qualité de votre code.
          </p>
          <button className="github-btn" onClick={handleLogin}>
            <img src="/assets/github-logo.svg" alt="GitHub" width="20" height="20" />
            Continuer avec GitHub
          </button>
        </div>
      </section>

      <section id="analyses" className="home-features-section">
        <h2 className="section-title">Ce que Commitclarify analyse</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-card-header">
              <ShieldAlert size={20} />
              <h3>Détection de secrets</h3>
            </div>
            <p>Identifie si des données sensibles sont présentes dans votre code.</p>
          </div>
          <div className="feature-card">
            <div className="feature-card-header">
              <FolderGit2 size={20} />
              <h3>Vérification .gitignore</h3>
            </div>
            <p>Vérifie que vos fichiers sensibles sont bien exclus du dépôt.</p>
          </div>
          <div className="feature-card">
            <div className="feature-card-header">
              <SearchCode size={20} />
              <h3>Qualite du code</h3>
            </div>
            <p>Detecte les fonctions trop longues, le code duplique et les mauvaises pratiques.</p>
          </div>
          <div className="feature-card">
            <div className="feature-card-header">
              <FileText size={20} />
              <h3>README vs Code</h3>
            </div>
            <p>Vérifie la présence et la pertinence de votre documentation.</p>
          </div>
        </div>
      </section>


      <section id="comment-ca-marche" className="how-it-works">
        <h2 className="section-title">Comment ça marche</h2>
        <div className="steps">
          <div className="step">
            <span className="step-number">1</span>
            <h3>Connectez-vous</h3>
            <p>Authentification via GitHub OAuth en un clic</p>
          </div>
          <div className="step">
            <span className="step-number">2</span>
            <h3>Choisissez un repo</h3>
            <p>Sélectionnez parmi vos repositories publics ou privés</p>
          </div>
          <div className="step">
            <span className="step-number">3</span>
            <h3>Lancez l'analyse</h3>
            <p>L'IA scanne votre code en quelques secondes</p>
          </div>
          <div className="step">
            <span className="step-number">4</span>
            <h3>Agissez</h3>
            <p>Recevez un rapport détaillé avec recommandations</p>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <span>&copy; 2026 Commitclarify. Tous droits reserves.</span>
        <div className="footer-links">
          <Link to="/privacy">Politique de confidentialite</Link>
          <Link to="/terms">Conditions d'utilisation</Link>
        </div>
      </footer>
    </div>
  )
}

export default Home
