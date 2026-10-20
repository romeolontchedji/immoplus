import type { TonBadge } from "@/ui/components/Card";

/** Statuts d'une annonce vus par le gérant (mêmes valeurs que `StatutAnnonce` côté serveur). */
export const STATUTS: Record<string, { libelle: string; ton: TonBadge }> = {
  draft: { libelle: "Brouillon", ton: "neutre" },
  processing: { libelle: "En traitement", ton: "information" },
  published: { libelle: "En ligne", ton: "succes" },
  hidden: { libelle: "Masquée", ton: "avertissement" },
  rented: { libelle: "Louée", ton: "marque" },
  archived: { libelle: "Archivée", ton: "neutre" },
  removed: { libelle: "Retirée", ton: "danger" },
};

export const RAISONS_MASQUAGE: Record<string, string> = {
  stale: "Masquée automatiquement. Remets-la en ligne si elle est toujours libre.",
  moderation: "Masquée par la modération. Contacte l'équipe Logeo pour en savoir plus.",
  owner: "Tu l'as masquée. Remets-la en ligne quand tu veux.",
  gerant_suspended: "Ton compte est suspendu : tes annonces sont masquées.",
};

/** Filtres de la liste « Mes annonces ». */
export const ONGLETS = [
  { cle: "tout", libelle: "Toutes", statuts: null },
  { cle: "ligne", libelle: "En ligne", statuts: ["published"] },
  { cle: "brouillons", libelle: "Brouillons", statuts: ["draft", "processing"] },
  { cle: "masquees", libelle: "Masquées", statuts: ["hidden"] },
  { cle: "louees", libelle: "Louées", statuts: ["rented", "archived"] },
] as const;

export function ilYA(dateIso: string | null | undefined): string | null {
  if (!dateIso) return null;
  const jours = Math.floor((Date.now() - new Date(dateIso).getTime()) / 86_400_000);
  if (jours <= 0) return "aujourd'hui";
  if (jours === 1) return "hier";
  return `il y a ${jours} jours`;
}
