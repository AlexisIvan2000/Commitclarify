# CommitClarify — interface

Front React de CommitClarify. L'utilisateur connecte son compte GitHub, choisit un dépôt,
et obtient un rapport sur ce qui est exposé ou négligé dans son code.

## Démarrer

```bash
npm install
npm run dev      # serveur de développement sur http://localhost:5173
npm run lint     # eslint + contrôle de parité des catalogues fr/en
npm run build    # build de production
```

L'API est attendue sur `http://localhost:8000`, surchargeable par `VITE_API_URL`.

## Organisation

```
src/
├── core/                partagé par toutes les features
│   ├── network/         client HTTP, stockage des jetons, erreurs typées
│   ├── translation/     catalogues fr/en, provider, détection de langue
│   ├── design/          tokens CSS, carte d'icônes sémantiques
│   ├── components/      Sidebar, Spinner, ErrorState, EmptyState, PageHeader…
│   ├── pages/           404, pages légales
│   └── utils/           dates, téléchargements
└── features/
    ├── authentication/  OAuth GitHub, session, compte
    ├── repositories/    liste des dépôts, filtres
    ├── scan/            lancement et suivi des analyses, quota
    ├── report/          rapport, export, approfondissement IA
    └── history/         analyses passées
```

Chaque feature suit le même découpage : `data/` (appels API), `domain/` (règles et
normalisation), `presentation/` (pages, composants, providers). `core` ne dépend
jamais d'une feature. La feature `scan` possède le vocabulaire des analyses ; les
autres l'importent.

## Deux points à connaître

**Le suivi des analyses vit au-dessus des pages.** `RunsProvider` est monté dans
`AppShell`, donc une analyse continue d'être suivie quand on navigue ailleurs, et un
rechargement de page la retrouve via `GET /analyze/active`. Une page ne lance jamais
une analyse sans passer par le provider.

**Les messages d'erreur sont localisés par code, pas par texte.** Le serveur répond en
anglais avec un `code` et des `params` ; le front cherche `apiErrors[code]` dans le
catalogue et interpole (`{seconds}`, `{limit}`). Ajouter un code côté serveur impose
d'ajouter son entrée dans `fr.js` et `en.js` — `npm run lint` échoue sinon.
