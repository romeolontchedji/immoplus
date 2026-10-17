# ADR 0005 — Verrou biométrique (mobile) et « Se souvenir de moi » (site)

- Statut : **accepté**
- Date : 2026-10-17 (décision V5 du porteur, `docs/plan-actions-v2.md` §2)

## Contexte

Les utilisateurs demandent une connexion par empreinte et une case « Se souvenir de moi ».

- **Mobile** : la session est déjà persistante (jeton de rafraîchissement de 30 jours avec rotation, CDC EF-AUT-04,
  rangé dans `expo-secure-store`). Le besoin réel n'est donc pas de « se connecter » par empreinte mais de
  **protéger l'application ouverte** quand le téléphone est prêté ou partagé (fréquent chez les étudiants).
- **Site** : la session Django persiste deux semaines par défaut, même sur un ordinateur partagé (cybercafé).

## Décision

### Mobile : verrou biométrique facultatif

- Nouvelle dépendance : **`expo-local-authentication`** (module officiel Expo, version alignée sur le SDK 57,
  installée par `npx expo install`). Aucune autre bibliothèque.
- Réglage **désactivé par défaut**, activable dans le Profil (« Déverrouiller avec l'empreinte ») seulement si le
  téléphone a un capteur **et** une empreinte (ou un visage) enregistré. L'activation exige une réussite biométrique.
- Verrouillage : au démarrage à froid, et au retour au premier plan après **5 minutes** en arrière-plan. L'écran de
  verrou propose « Déverrouiller » (biométrie, avec repli sur le code du téléphone) et « Se déconnecter ».
- Le réglage est **local à l'appareil** (stockage clé-valeur) ; aucune donnée biométrique ne quitte le téléphone ni
  n'est connue de l'application (le système répond seulement « réussi » ou « échoué »). Aucun changement serveur.
- La déconnexion efface le réglage.

### Site : « Se souvenir de moi »

- Case **décochée par défaut** sur la page de connexion. Cochée : session de **30 jours**. Décochée : session
  limitée au navigateur (fermée avec lui), protection des ordinateurs partagés.
- La règle d'invalidation existante est conservée (changement de mot de passe, révocation : `token_version`).

## Conséquences

- Une dépendance mobile de plus (module natif) : le verrou ne fonctionne pas sous Expo Go sans le module ; il se
  désactive de lui-même si le module ou le capteur manque.
- Le verrou ne remplace pas l'authentification serveur : un jeton volé reste révocable depuis « Appareils
  connectés ». Une évolution possible est d'exiger la biométrie pour lire le jeton dans `SecureStore`
  (`requireAuthentication`), écartée ici : elle bloquerait les tâches en arrière-plan (notifications).
- Décision hors CDC : à reporter dans `docs/cahier-des-charges.md` (EF-AUT-04) si elle est retenue durablement.
