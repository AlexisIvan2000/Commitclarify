import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import HomeNavbar from '../components/HomeNavbar'

function Terms() {
  const navigate = useNavigate()

  return (
    <div className="page-wrapper fade-in">
      <HomeNavbar />
      <div className="legal-page">
        <button className="back-btn" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Retour
        </button>

      <h1>Conditions d'utilisation</h1>
      <p className="legal-date">Derniere mise a jour : 12 mars 2026</p>

      <section>
        <h2>1. Acceptation des conditions</h2>
        <p>
          En utilisant CommitClarify, vous acceptez les presentes conditions d'utilisation.
          Si vous n'acceptez pas ces conditions, veuillez ne pas utiliser le service.
        </p>
      </section>

      <section>
        <h2>2. Description du service</h2>
        <p>
          CommitClarify est un outil d'analyse automatisee de repositories GitHub.
          Il detecte les problemes de securite, de qualite de code et de coherence documentaire
          a l'aide d'intelligence artificielle et d'outils de linting.
        </p>
      </section>

      <section>
        <h2>3. Limites d'utilisation</h2>
        <ul>
          <li>Chaque utilisateur est limite a <strong>3 analyses par jour</strong>.</li>
          <li>Le service est fourni "en l'etat" sans garantie de disponibilite.</li>
          <li>Les resultats d'analyse sont indicatifs et ne constituent pas un audit de securite professionnel.</li>
        </ul>
      </section>

      <section>
        <h2>4. Responsabilites</h2>
        <p>
          CommitClarify ne saurait etre tenu responsable des decisions prises sur la base des rapports generes.
          L'utilisateur reste seul responsable de la securite et de la qualite de son code.
        </p>
      </section>

      <section>
        <h2>5. Propriete intellectuelle</h2>
        <p>
          Vous conservez l'integralite des droits sur votre code source.
          CommitClarify n'acquiert aucun droit sur le code analyse.
          Les rapports generes vous appartiennent.
        </p>
      </section>

      <section>
        <h2>6. Compte utilisateur</h2>
        <ul>
          <li>Un compte est cree automatiquement lors de la premiere connexion via GitHub.</li>
          <li>Vous pouvez supprimer votre compte a tout moment. Cette action est irreversible.</li>
          <li>La suppression du compte n'annule pas les limites d'utilisation quotidiennes.</li>
        </ul>
      </section>

      <section>
        <h2>7. Modifications</h2>
        <p>
          Nous nous reservons le droit de modifier ces conditions a tout moment.
          Les modifications prennent effet des leur publication sur cette page.
        </p>
      </section>

      <section>
        <h2>8. Contact</h2>
        <p>Pour toute question, contactez-nous a : <strong>contact@commitclarify.com</strong></p>
      </section>
      </div>
    </div>
  )
}

export default Terms
