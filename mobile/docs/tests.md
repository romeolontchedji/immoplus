# Tests

| Niveau | Outil | Où | Contenu |
|---|---|---|---|
| Unitaires | Jest (`jest-expo`) | `src/__tests__` | client HTTP (en-têtes, 426, 503, renouvellement 401, `unwrap`), session, file d'envoi, client temps réel (reconnexion, ping, codes de fermeture, focus), fusion des messages, cache temps réel, routage des notifications, filtres, brouillon, formats, téléphone, versions |
| Composants | `@testing-library/react-native` (installé) | à écrire | écrans et formulaires — premier travail à faire sur les squelettes |
| Parcours | Maestro | `maestro/*.yaml` | connexion, recherche → fiche → message, alerte, déconnexion (à lancer sur appareil ou émulateur) |

`npm run verifier` = typage + lint + tests avec couverture. Le seuil de couverture (70 %) porte sur la logique testée sans appareil
(client HTTP, session, temps réel, stockage, utilitaires, règles pures) ; les crochets de données et les écrans ne sont pas comptés tant qu'ils n'ont pas de tests de composants.
