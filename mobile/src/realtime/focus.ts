/** Conversation actuellement à l'écran (ou null). Lue par le gestionnaire de notifications au premier plan : pas de bannière pour ce qu'on regarde déjà. */
let courant: string | null = null;
export const focusActuel = (): string | null => courant;
export const definirFocusActuel = (id: string | null): void => {
  courant = id;
};
