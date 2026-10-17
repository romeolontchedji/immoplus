import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { francs } from "@/lib/format";

/** Critères de recherche (EF-REC-05). Partagés entre l'écran de recherche et la feuille de filtres ; en mémoire seulement. */
export type Filtres = {
  q: string;
  district: string[]; // slugs
  type: string[];
  water: string[]; // running, well, borehole
  rent_max?: number;
  bathroom?: boolean;
  fenced?: boolean;
  max_distance_m?: number;
  sort: "recent" | "rent_asc" | "rent_desc" | "distance";
};

export const FILTRES_VIDES: Filtres = { q: "", district: [], type: [], water: [], sort: "recent" };

export const LIBELLES_TRI: Record<Filtres["sort"], string> = { recent: "Plus récentes", rent_asc: "Moins chères", rent_desc: "Plus chères", distance: "Plus près de l'UP" };
export const LIBELLES_EAU: Record<string, string> = { running: "Eau courante", well: "Puits", borehole: "Forage" };

/** Paramètres de requête de GET /v1/listings : listes séparées par des virgules, valeurs absentes omises. */
export function versParametres(f: Filtres, cursor?: string): Record<string, string | number | boolean | undefined> {
  return {
    q: f.q.trim() || undefined,
    district: f.district.length ? f.district.join(",") : undefined,
    type: f.type.length ? f.type.join(",") : undefined,
    water: f.water?.length ? f.water.join(",") : undefined,
    rent_max: f.rent_max,
    bathroom: f.bathroom ? true : undefined,
    fenced: f.fenced ? true : undefined,
    max_distance_m: f.max_distance_m,
    sort: f.sort,
    cursor,
  };
}

export function nombreDeFiltres(f: Filtres): number {
  return [f.district.length > 0, f.type.length > 0, (f.water?.length ?? 0) > 0, f.rent_max !== undefined, f.bathroom, f.fenced, f.max_distance_m !== undefined].filter(Boolean).length;
}

/** Un filtre actif, affiché en pastille retirable sous la barre de recherche. */
export type FiltreActif = { cle: string; libelle: string; retirer: (f: Filtres) => Filtres };

/** Liste des filtres actifs (hors texte libre et tri) ; `quartiers` donne le nom affiché d'un slug. */
export function filtresActifs(f: Filtres, quartiers: Record<string, string>, typeLibelle: (t: string) => string): FiltreActif[] {
  const sans = <T,>(liste: T[], v: T) => liste.filter((x) => x !== v);
  return [
    ...f.district.map((d) => ({ cle: `q-${d}`, libelle: quartiers[d] ?? d, retirer: (x: Filtres) => ({ ...x, district: sans(x.district, d) }) })),
    ...f.type.map((t) => ({ cle: `t-${t}`, libelle: typeLibelle(t), retirer: (x: Filtres) => ({ ...x, type: sans(x.type, t) }) })),
    ...(f.water ?? []).map((w) => ({ cle: `e-${w}`, libelle: LIBELLES_EAU[w] ?? w, retirer: (x: Filtres) => ({ ...x, water: sans(x.water, w) }) })),
    ...(f.rent_max !== undefined ? [{ cle: "budget", libelle: `≤ ${francs(f.rent_max)}`, retirer: (x: Filtres) => ({ ...x, rent_max: undefined }) }] : []),
    ...(f.max_distance_m !== undefined ? [{ cle: "distance", libelle: `≤ ${f.max_distance_m} m de l'UP`, retirer: (x: Filtres) => ({ ...x, max_distance_m: undefined }) }] : []),
    ...(f.bathroom ? [{ cle: "douche", libelle: "Douche interne", retirer: (x: Filtres) => ({ ...x, bathroom: undefined }) }] : []),
    ...(f.fenced ? [{ cle: "cloture", libelle: "Cour clôturée", retirer: (x: Filtres) => ({ ...x, fenced: undefined }) }] : []),
  ];
}

type Valeur = { filtres: Filtres; definir: (f: Filtres) => void; reinitialiser: () => void };
const Ctx = createContext<Valeur | null>(null);

export function FiltresProvider({ children }: { children: ReactNode }) {
  const [filtres, definir] = useState<Filtres>(FILTRES_VIDES);
  const valeur = useMemo<Valeur>(() => ({ filtres, definir, reinitialiser: () => definir(FILTRES_VIDES) }), [filtres]);
  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

export function useFiltres(): Valeur {
  const v = useContext(Ctx);
  if (!v) throw new Error("useFiltres doit être utilisé dans <FiltresProvider>.");
  return v;
}
