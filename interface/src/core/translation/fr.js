const fr = {
  languageName: 'Français',

  actions: {
    back: 'Retour',
    backHome: 'Retour à l\'accueil',
    retry: 'Réessayer',
    view: 'Voir',
    deleteAll: 'Tout supprimer',
    deleteAnalysisOf: 'Supprimer l\'analyse de',
    logout: 'Déconnexion',
    deleteAccount: 'Supprimer mon compte',
    analyze: 'Analyser',
    exportPdf: 'Export PDF',
    exportJson: 'Export JSON',
    fullReport: 'Voir le rapport complet',
    history: 'Historique',
    repos: 'Repos',
    all: 'Tous',
    search: 'Rechercher...',
  },

  errors: {
    network: 'Connexion au serveur impossible. Vérifiez votre réseau puis réessayez.',
    unexpected: 'Une erreur inattendue est survenue.',
    unauthorized: 'Votre session a expiré, reconnectez-vous.',
    forbidden: 'Accès refusé.',
    notFound: 'Ressource introuvable.',
    conflict: 'Cette analyse est déjà en cours ou déjà terminée.',
    quota: 'Quota quotidien atteint. Revenez demain.',
    server: 'Le serveur a rencontré une erreur. Réessayez dans quelques instants.',
    streamUnavailable: 'Le flux d\'analyse est indisponible.',
    reposFailed: 'Impossible de récupérer vos repositories.',
    historyFailed: 'Impossible de charger l\'historique.',
    analysisNotFound: 'Analyse introuvable.',
    exportFailed: 'Le téléchargement a échoué.',
    deleteFailed: 'La suppression a échoué.',
    deleteAccountFailed: 'La suppression du compte a échoué.',
    loginFailed: 'La connexion a échoué. Réessayez.',
    renderCrash: 'Cette page n\'a pas pu s\'afficher.',
  },

  apiErrors: {
    unauthorized: 'Votre session a expiré, reconnectez-vous.',
    validation_error: 'La requête est invalide.',
    not_found: 'Ressource introuvable.',
    conflict: 'Cette action est déjà en cours ou déjà effectuée.',
    analysis_running: 'Cette analyse est déjà en cours.',
    analysis_finished: 'Cette analyse est déjà terminée. Consultez son rapport ou lancez-en une nouvelle.',
    quota_exceeded: 'Quota quotidien atteint. Revenez demain.',
    external_service_error: 'Un service externe est indisponible. Réessayez dans quelques instants.',
    internal_error: 'Le serveur a rencontré une erreur.',
  },

  auth: {
    loggingIn: 'Connexion en cours...',
    loading: 'Chargement...',
    continueWithGithub: 'Continuer avec GitHub',
    memberSince: 'Membre depuis',
    quotaRemaining: 'analyses restantes aujourd\'hui',
    confirmDeleteAccount: 'Supprimer définitivement votre compte et toutes vos données ?',
    interfaceLanguage: 'Langue de l\'interface',
    callbackErrors: {
      state_invalide: 'La vérification de sécurité a échoué. Relancez la connexion.',
      echec_authentification: 'GitHub n\'a pas pu confirmer votre identité. Réessayez.',
      access_denied: 'Vous avez refusé l\'accès à votre compte GitHub.',
    },
  },

  analysis: {
    stepLabels: {
      secrets_detection: 'Détection de secrets',
      gitignore_check: 'Vérification .gitignore',
      quality_check: 'Qualité du code',
      readme_check: 'README vs Code',
    },
    stepperLabels: {
      fetching: 'Récupération',
      indexing: 'Indexation',
      analyzing: 'Analyse IA',
      done: 'Terminé',
    },
    statusLabels: {
      completed: 'Terminée',
      processing: 'En cours',
      pending: 'En attente',
      failed: 'Échouée',
    },
    phases: {
      starting: 'Démarrage...',
      streaming: 'Analyse en cours...',
      done: 'Terminée',
      error: 'Erreur',
    },
    title: 'Analyse de',
    reportTitle: 'Rapport :',
    issues: 'Problèmes',
    recommendations: 'Recommandations',
    clean: 'Aucun problème détecté.',
    pending: 'En attente...',
    untitledIssue: 'Problème sans intitulé',
    untitledRecommendation: 'Recommandation sans intitulé',
    files: 'fichiers',
    skipped: 'ignorés',
    emptyResults: 'Cette analyse ne contient aucun résultat.',
    historyTitle: 'Historique des analyses',
    historyEmpty: 'Aucune analyse effectuée.',
    confirmDeleteAll: 'Supprimer tout l\'historique ?',
    reposTitle: 'Vos repositories',
    reposEmpty: 'Aucun repository trouvé.',
    reposNoMatch: 'Aucun repository ne correspond aux filtres.',
    visibility: 'Visibilité',
    language: 'Langage',
    public: 'Public',
    private: 'Privé',
    reportLanguage: 'Langue du rapport',
    reportLanguageHint: 'Les rapports sont figés dans la langue choisie au lancement.',
    generatedIn: 'Rapport généré en',
  },

  notFound: {
    title: 'Page introuvable',
    text: 'La page que vous cherchez n\'existe pas ou a été déplacée.',
  },

  home: {
    tagline1: 'Le gardien intelligent de vos repositories.',
    tagline2: 'Analysez la sécurité, la cohérence et la qualité de votre code.',
    featuresTitle: 'Ce que Commitclarify analyse',
    features: [
      {
        key: 'secrets',
        title: 'Détection de secrets',
        text: 'Identifie si des données sensibles sont présentes dans votre code.',
      },
      {
        key: 'gitignore',
        title: 'Vérification .gitignore',
        text: 'Vérifie que vos fichiers sensibles sont bien exclus du dépôt.',
      },
      {
        key: 'quality',
        title: 'Qualité du code',
        text: 'Détecte les fonctions trop longues, le code dupliqué et les mauvaises pratiques.',
      },
      {
        key: 'readme',
        title: 'README vs Code',
        text: 'Vérifie la présence et la pertinence de votre documentation.',
      },
    ],
    stepsTitle: 'Comment ça marche',
    steps: [
      { key: 'login', title: 'Connectez-vous', text: 'Authentification via GitHub OAuth en un clic' },
      { key: 'repo', title: 'Choisissez un repo', text: 'Sélectionnez parmi vos repositories publics ou privés' },
      { key: 'run', title: 'Lancez l\'analyse', text: 'L\'IA scanne votre code en quelques secondes' },
      { key: 'act', title: 'Agissez', text: 'Recevez un rapport détaillé avec recommandations' },
    ],
    navAnalyses: 'Analyses',
    navHowItWorks: 'Comment ça marche',
    rights: '© 2026 Commitclarify. Tous droits réservés.',
    privacyLink: 'Politique de confidentialité',
    termsLink: 'Conditions d\'utilisation',
  },

  legal: {
    updatedAt: 'Dernière mise à jour :',
    updatedDate: '12 mars 2026',
    privacyTitle: 'Politique de confidentialité',
    privacy: [
      {
        title: '1. Données collectées',
        paragraphs: ['CommitClarify collecte uniquement les données nécessaires à son fonctionnement :'],
        items: [
          { term: 'Informations GitHub', text: 'identifiant, nom d\'utilisateur, adresse email et avatar via OAuth.' },
          { term: 'Code source', text: 'le contenu de vos repositories est récupéré temporairement pour analyse. Il n\'est pas stocké de manière permanente.' },
          { term: 'Résultats d\'analyse', text: 'les rapports générés sont conservés dans votre historique.' },
        ],
      },
      {
        title: '2. Utilisation des données',
        paragraphs: ['Vos données sont utilisées exclusivement pour :'],
        items: [
          { text: 'Authentifier votre accès via GitHub OAuth.' },
          { text: 'Analyser le code source de vos repositories.' },
          { text: 'Générer et stocker vos rapports d\'analyse.' },
        ],
      },
      {
        title: '3. Partage des données',
        paragraphs: ['Vos données ne sont jamais vendues ni partagées avec des tiers, à l\'exception des services techniques nécessaires :'],
        items: [
          { term: 'GitHub API', text: 'pour accéder à vos repositories.' },
          { term: 'OpenAI API', text: 'des extraits de code anonymisés sont envoyés pour l\'analyse IA. Aucune donnée personnelle n\'est transmise.' },
        ],
      },
      {
        title: '4. Sécurité',
        paragraphs: [
          'Les tokens d\'accès GitHub sont chiffrés (Fernet) avant stockage. Les communications sont sécurisées via HTTPS. Les mots de passe et secrets ne sont jamais stockés en clair.',
        ],
        items: [],
      },
      {
        title: '5. Suppression des données',
        paragraphs: [
          'Vous pouvez supprimer votre compte à tout moment depuis le menu utilisateur. Cette action supprime définitivement votre profil, vos analyses et vos résultats.',
        ],
        items: [],
      },
      {
        title: '6. Contact',
        paragraphs: ['Pour toute question concernant vos données, contactez-nous à : contact@commitclarify.com'],
        items: [],
      },
    ],
    termsTitle: 'Conditions d\'utilisation',
    terms: [
      {
        title: '1. Acceptation des conditions',
        paragraphs: [
          'En utilisant CommitClarify, vous acceptez les présentes conditions d\'utilisation. Si vous n\'acceptez pas ces conditions, veuillez ne pas utiliser le service.',
        ],
        items: [],
      },
      {
        title: '2. Description du service',
        paragraphs: [
          'CommitClarify est un outil d\'analyse automatisée de repositories GitHub. Il détecte les problèmes de sécurité, de qualité de code et de cohérence documentaire à l\'aide d\'intelligence artificielle et d\'outils de linting.',
        ],
        items: [],
      },
      {
        title: '3. Limites d\'utilisation',
        paragraphs: [],
        items: [
          { text: 'Chaque utilisateur est limité à 3 analyses par jour.' },
          { text: 'Le service est fourni « en l\'état » sans garantie de disponibilité.' },
          { text: 'Les résultats d\'analyse sont indicatifs et ne constituent pas un audit de sécurité professionnel.' },
        ],
      },
      {
        title: '4. Responsabilités',
        paragraphs: [
          'CommitClarify ne saurait être tenu responsable des décisions prises sur la base des rapports générés. L\'utilisateur reste seul responsable de la sécurité et de la qualité de son code.',
        ],
        items: [],
      },
      {
        title: '5. Propriété intellectuelle',
        paragraphs: [
          'Vous conservez l\'intégralité des droits sur votre code source. CommitClarify n\'acquiert aucun droit sur le code analysé. Les rapports générés vous appartiennent.',
        ],
        items: [],
      },
      {
        title: '6. Compte utilisateur',
        paragraphs: [],
        items: [
          { text: 'Un compte est créé automatiquement lors de la première connexion via GitHub.' },
          { text: 'Vous pouvez supprimer votre compte à tout moment. Cette action est irréversible.' },
          { text: 'La suppression du compte n\'annule pas les limites d\'utilisation quotidiennes.' },
        ],
      },
      {
        title: '7. Modifications',
        paragraphs: [
          'Nous nous réservons le droit de modifier ces conditions à tout moment. Les modifications prennent effet dès leur publication sur cette page.',
        ],
        items: [],
      },
      {
        title: '8. Contact',
        paragraphs: ['Pour toute question, contactez-nous à : contact@commitclarify.com'],
        items: [],
      },
    ],
  },
}

export default fr
