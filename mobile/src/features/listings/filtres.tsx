import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/** Critères de recherche (EF-REC-05). Partagés entre l'écran de recherche et la feuille de filtres ; en mémoire seulement. */
export type Filtres = {
  q: string;
  district: string[]; // slugs
  type: string[];
  rent_max?: number;
  bathroom?: boolean;
  fenced?: boolean;
  max_distance_m?: number;
  sort: "recent" | "rent_asc" | "rent_desc" | "distance";
};

export const FILTRES_VIDES: Filtres = { q: "", district: [], type: [], sort: "recent" };

/** Paramètres de requête de GET /v1/listings : listes séparées par des virgules, valeurs absentes omises. */
export function versParametres(f: Filtres, cursor?: string): Record<string, string | number | boolean | undefined> {
  return {
    q: f.q.trim() || undefined,
    district: f.district.length ? f.district.join(",") : undefined,
    type: f.type.length ? f.type.join(",") : undefined,
    rent_max: f.rent_max,
    bathroom: f.bathroom ? true : undefined,
    fenced: f.fenced ? true : undefined,
    max_distance_m: f.max_distance_m,
    sort: f.sort,
    cursor,
  };
}

export function nombreDeFiltres(f: Filtres): number {
  return [f.district.length > 0, f.type.length > 0, f.rent_max !== undefined, f.bathroom, f.fenced, f.max_distance_m !== undefined].filter(Boolean).length;
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
