import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import HomeNavbar from '../components/HomeNavbar'

function Privacy() {
  const navigate = useNavigate()

  return (
    <div className="page-wrapper fade-in">
      <HomeNavbar />
      <div className="legal-page">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Retour
        </button>

      <h1>Politique de confidentialite</h1>
      <p className="legal-date">Derniere mise a jour : 12 mars 2026</p>

      <section>
        <h2>1. Donnees collectees</h2>
        <p>
          CommitClarify collecte uniquement les donnees necessaires a son fonctionnement :
        </p>
        <ul>
          <li><strong>Informations GitHub</strong> : identifiant, nom d'utilisateur, adresse email et avatar via OAuth.</li>
          <li><strong>Code source</strong> : le contenu de vos repositories est recupere temporairement pour analyse. Il n'est pas stocke de maniere permanente.</li>
          <li><strong>Resultats d'analyse</strong> : les rapports generes sont conserves dans votre historique.</li>
        </ul>
      </section>

      <section>
        <h2>2. Utilisation des donnees</h2>
        <p>Vos donnees sont utilisees exclusivement pour :</p>
        <ul>
          <li>Authentifier votre acces via GitHub OAuth.</li>
          <li>Analyser le code source de vos repositories.</li>
          <li>Generer et stocker vos rapports d'analyse.</li>
        </ul>
      </section>

      <section>
        <h2>3. Partage des donnees</h2>
        <p>
          Vos donnees ne sont jamais vendues ni partagees avec des tiers, a l'exception des services techniques necessaires :
        </p>
        <ul>
          <li><strong>GitHub API</strong> : pour acceder a vos repositories.</li>
          <li><strong>OpenAI API</strong> : des extraits de code anonymises sont envoyes pour l'analyse IA. Aucune donnee personnelle n'est transmise.</li>
        </ul>
      </section>

      <section>
        <h2>4. Securite</h2>
        <p>
          Les tokens d'acces GitHub sont chiffres (Fernet) avant stockage. Les communications sont securisees via HTTPS.
          Les mots de passe et secrets ne sont jamais stockes en clair.
        </p>
      </section>

      <section>
        <h2>5. Suppression des donnees</h2>
        <p>
          Vous pouvez supprimer votre compte a tout moment depuis le menu utilisateur.
          Cette action supprime definitivement votre profil, vos analyses et vos resultats.
        </p>
      </section>

      <section>
        <h2>6. Contact</h2>
        <p>Pour toute question concernant vos donnees, contactez-nous a : <strong>contact@commitclarify.com</strong></p>
      </section>
      </div>
    </div>
  )
}

export default Privacy
