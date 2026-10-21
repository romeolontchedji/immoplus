import { focusActuel } from "@/realtime/focus";

/** File de la bannière interne (plan v2, N5), sans interface : le temps réel y dépose, BanniereInterne l'affiche. */
export type Annonce = { titre: string; corps: string; kind: string; data: Record<string, unknown> };

let courante: Annonce | null = null;
const abonnes = new Set<() => void>();

export const annonces = {
  lire: (): Annonce | null => courante,
  abonner(f: () => void): () => void {
    abonnes.add(f);
    return () => void abonnes.delete(f);
  },
  changer(a: Annonce | null): void {
    courante = a;
    abonnes.forEach((f) => f());
  },
};

/** Jamais pour la conversation déjà à l'écran. */
export function annoncerNotification(n: { title: string; body: string; kind: string; data?: Record<string, unknown> }): void {
  const data = n.data ?? {};
  if (n.kind === "message.received" && data.conversation_id === focusActuel()) return;
  annonces.changer({ titre: n.title, corps: n.body, kind: n.kind, data });
}
