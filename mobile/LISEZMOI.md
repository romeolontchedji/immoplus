# mobile/

Application mobile Immo+ (partie 2) : Expo / React Native avec Expo Router.

Elle consomme l'API `/v1` du serveur (`docs/api/openapi.json`) et le temps réel sous `/ws/`.
Le contrat d'API est versionné dans le dépôt et sert de point de départ au client TypeScript.

## Démarrer

```bash
npm install
npm start          # Expo (dev client)
npm run android    # ou npm run ios
```

## Contrôles

```bash
npm run typecheck  # TypeScript
npm run lint       # ESLint
npm test           # Jest
npm run verifier   # typecheck + lint + tests
```

## Documentation

- `docs/architecture.md` : architecture et organisation du code.
- `docs/ecrans.md` : correspondance écrans / maquettes (`docs/design/screens/`).
- `docs/plan-action-mobile.md` : plan d'action.
- `docs/avancement-mobile.md` : état d'avancement.
- `docs/tests.md` et `maestro/` : tests unitaires et scénarios de bout en bout.
