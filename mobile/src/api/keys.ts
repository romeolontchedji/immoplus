/** Clés de cache TanStack Query : une seule source, pour que le temps réel et les mutations invalident au même endroit. */
export const qk = {
  appConfig: ["app-config"] as const,
  me: ["me"] as const,
  districts: ["districts"] as const,
  fil: (filtres: unknown) => ["fil", filtres] as const,
  fiche: (ident: string) => ["fiche", ident] as const,
  favoris: ["favoris"] as const,
  alertes: ["alertes"] as const,
  conversations: ["conversations"] as const,
  conversation: (id: string) => ["conversation", id] as const,
  messages: (id: string) => ["messages", id] as const,
  notifications: ["notifications"] as const,
  nonLues: ["notifications", "non-lues"] as const,
  appareils: ["appareils"] as const,
  preferencesNotif: ["preferences-notifications"] as const,
  pro: {
    tableau: ["pro", "tableau"] as const,
    annonces: ["pro", "annonces"] as const,
    annonce: (id: string) => ["pro", "annonce", id] as const,
    medias: (id: string) => ["pro", "medias", id] as const,
  },
};
