import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { CLES_KV, kv } from "@/storage/kv";

/**
 * Brouillon local de l'assistant de création d'annonce. Le serveur exige tous les champs obligatoires dès la création
 * (`POST /v1/pro/listings`) : les étapes « infos », « localisation » et « équipements » s'accumulent donc ici, sur l'appareil
 * (persisté, l'assistant reprend là où il s'est arrêté), puis l'annonce est créée côté serveur à la fin de l'étape « équipements ».
 * Ensuite, `serveurId` est renseigné et les étapes « médias », « description » et « publication » travaillent sur le serveur.
 */
export type Brouillon = {
  serveurId?: string;
  title?: string;
  room_type?: string;
  rent_amount?: number;
  deposit_months?: number;
  advance_months?: number;
  agent_fee_amount?: number;
  available_from?: string; // AAAA-MM-JJ
  district?: string; // identifiant du quartier
  landmark_text?: string;
  address_private?: string;
  latitude?: string; // facultatif (décision V7) : GPS du téléphone, sinon le serveur prend le centre du quartier
  longitude?: string;
  has_private_bathroom?: boolean;
  is_fenced?: boolean;
  water_sources?: string[]; // plusieurs sources possibles : forage, puits, compteur…
  electricity_meter?: string;
  kitchen?: string; // private, shared, none (plan v3, C2)
  rent_negotiable?: boolean; // loyer à débattre (plan v3, C3)
  description_md?: string; // « Autres détails », texte simple
};

/** Champs obligatoires pour créer l'annonce côté serveur. */
export const CHAMPS_CREATION = [
  "title", "room_type", "rent_amount", "deposit_months", "advance_months", "available_from", "district", "landmark_text",
  "address_private", "has_private_bathroom", "is_fenced", "water_sources", "electricity_meter", "kitchen",
] as const satisfies readonly (keyof Brouillon)[];

export function champsManquants(b: Brouillon): (typeof CHAMPS_CREATION)[number][] {
  return CHAMPS_CREATION.filter((c) => b[c] === undefined || b[c] === "" || (Array.isArray(b[c]) && b[c].length === 0));
}

type Valeur = { brouillon: Brouillon; maj: (m: Partial<Brouillon>) => void; effacer: () => void; charge: boolean };
const Ctx = createContext<Valeur | null>(null);

export function BrouillonProvider({ children }: { children: ReactNode }) {
  const [brouillon, setBrouillon] = useState<Brouillon>({});
  const [charge, setCharge] = useState(false);

  useEffect(() => {
    void kv.get<Brouillon & { water_source?: string }>(CLES_KV.brouillon).then((b) => {
      if (b) {
        // Brouillon d'avant le choix multiple de l'eau : la source unique devient une liste.
        const { water_source, ...reste } = b;
        setBrouillon(water_source && !reste.water_sources ? { ...reste, water_sources: [water_source] } : reste);
      }
      setCharge(true);
    });
  }, []);

  const maj = useCallback((m: Partial<Brouillon>) => {
    setBrouillon((b) => {
      const suivant = { ...b, ...m };
      void kv.set(CLES_KV.brouillon, suivant); // enregistré à chaque étape (CDC §12.3)
      return suivant;
    });
  }, []);
  const effacer = useCallback(() => {
    setBrouillon({});
    void kv.remove(CLES_KV.brouillon);
  }, []);

  const valeur = useMemo(() => ({ brouillon, maj, effacer, charge }), [brouillon, maj, effacer, charge]);
  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

export function useBrouillon(): Valeur {
  const v = useContext(Ctx);
  if (!v) throw new Error("useBrouillon doit être utilisé dans <BrouillonProvider>.");
  return v;
}
