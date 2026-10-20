/** Textes de l'application (français). Un seul fichier tant qu'une seule langue est livrée ; `t()` garde la porte ouverte. */
const fr = {
  commun: {
    reessayer: "Réessayer", annuler: "Annuler", continuer: "Continuer", enregistrer: "Enregistrer", fermer: "Fermer", retour: "Retour",
    chargement: "Chargement…", horsLigne: "Pas de connexion. Les données affichées peuvent être anciennes.", erreurGenerique: "Une erreur est survenue.",
    connexionRequise: "Connecte-toi pour continuer.", seConnecter: "Se connecter", voirPlus: "Voir plus",
  },
  onglets: { accueil: "Accueil", recherche: "Recherche", messages: "Messages", alertes: "Alertes", profil: "Profil", tableau: "Tableau de bord", annonces: "Annonces" },
  auth: {
    telephone: "Numéro de téléphone", motDePasse: "Mot de passe", code: "Code reçu par SMS", nom: "Nom complet", cgu: "J'accepte les conditions d'utilisation",
    seConnecter: "Se connecter", creerCompte: "Créer un compte", motDePasseOublie: "Mot de passe oublié ?", envoyerCode: "Recevoir le code", renvoyerDans: "Renvoyer le code dans",
  },
  erreurs: {
    // Messages montrés à l'utilisateur, par code d'erreur de l'API. Le serveur renvoie aussi un message : il sert de repli.
    invalid_credentials: "Numéro ou mot de passe incorrect.",
    account_suspended: "Ton compte est suspendu. Tu peux consulter les annonces mais pas écrire.",
    rate_limited: "Trop de tentatives. Réessaie dans un moment.",
    contact_detected: "Les coordonnées (numéro, e-mail, lien) ne sont pas autorisées : garde les échanges dans Immo+.",
    conversation_blocked: "Cette conversation est bloquée.",
    conversation_read_only: "Cette conversation est en lecture seule.",
    listing_unavailable: "Cette annonce n'est plus disponible.",
    alerts_limit: "Tu as atteint le nombre maximal d'alertes actives.",
    upgrade_required: "Mets Immo+ à jour pour continuer.",
    maintenance: "Immo+ est en maintenance. Réessaie dans quelques minutes.",
    network: "Pas de connexion. Vérifie ton réseau et réessaie.",
    upload_quota: "Limite atteinte : une vidéo et 10 photos par annonce, deux envois à la fois au plus.",
    media_required: "Une annonce en ligne garde sa vidéo et au moins 3 photos. Masque-la d’abord, ou ajoute la nouvelle photo avant de retirer l’ancienne.",
    listing_locked: "Cette annonce n'accepte plus de médias.",
    storage_full: "Le stockage du serveur est plein. Réessaie plus tard.",
    upload_too_large: "Le fichier est trop lourd.",
  } as Record<string, string>,
  statutAnnonce: { draft: "Brouillon", processing: "En traitement", published: "En ligne", hidden: "Masquée", rented: "Louée", archived: "Archivée", removed: "Retirée" } as Record<string, string>,
  // Repli hors ligne : types officiels (la liste vivante vient de GET /v1/room-types, décision V1).
  typeChambre: {
    single: "Chambre simple", entree_coucher: "Entrée-coucher", chambre_salon: "Chambre-salon", studio: "Studio",
    studio_meuble: "Studio meublé", colocation: "Chambre en colocation", residence_etudiante: "Chambre en résidence étudiante",
    appartement_2_chambres: "Appartement 2 chambres salon", appartement_3_chambres: "Appartement 3 chambres salon et plus",
    appartement_meuble: "Appartement meublé", maison: "Maison individuelle", duplex: "Duplex", villa: "Villa",
  } as Record<string, string>,
};

export type Textes = typeof fr;
export const t = fr;

/** Message pour un code d'erreur de l'API, avec repli sur le message du serveur puis sur un texte générique. */
export function messageErreur(code: string | undefined, serveur?: string): string {
  return (code && fr.erreurs[code]) || serveur || fr.commun.erreurGenerique;
}
