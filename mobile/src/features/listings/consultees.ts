import { useSyncExternalStore } from "react";
import { CLES_KV, kv } from "@/storage/kv";

/** Dernières chambres consultées (plan v2, W6 côté app) : sur l'appareil seulement, 8 au plus, la plus récente d'abord. */
export type Consultee = { slug: string; title: string; rent_amount: number; district: string; image?: string };

const MAX = 8;
let liste: Consultee[] = [];
const abonnes = new Set<() => void>();
const publier = (nouvelle: Consultee[]) => {
  liste = nouvelle;
  abonnes.forEach((f) => f());
  void kv.set(CLES_KV.consultees, nouvelle);
};
void kv.get<Consultee[]>(CLES_KV.consultees).then((l) => {
  if (Array.isArray(l)) {
    liste = l.slice(0, MAX);
    abonnes.forEach((f) => f());
  }
});

/** Ajoute (ou remonte) une chambre en tête de l'historique. */
export function noterConsultation(c: Consultee): void {
  publier([c, ...liste.filter((x) => x.slug !== c.slug)].slice(0, MAX));
}

export function effacerConsultees(): void {
  publier([]);
}

export function useConsultees(): Consultee[] {
  return useSyncExternalStore((f) => (abonnes.add(f), () => void abonnes.delete(f)), () => liste);
}

/** Pour les tests. */
export const _consultees = { lire: () => liste, max: MAX };
