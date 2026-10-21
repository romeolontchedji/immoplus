import { useCallback, useEffect, useState } from "react";
import { CLES_KV, kv } from "@/storage/kv";

export type Preferences = {
  economieDonnees: boolean;
};

const DEFAUTS: Preferences = { economieDonnees: false };

/** État global des préférences en mémoire (évite une lecture AsyncStorage à chaque rendu). */
let cache: Preferences | null = null;
const abonnes = new Set<() => void>();

function notifier() {
  abonnes.forEach((fn) => fn());
}

async function charger(): Promise<Preferences> {
  const stocke = await kv.get<Preferences>(CLES_KV.preferences);
  cache = { ...DEFAUTS, ...stocke };
  notifier();
  return cache;
}

/**
 * Préférences locales (non-secrètes, stockées dans AsyncStorage).
 * Ne provoque qu'un seul appel AsyncStorage au montage de la première instance.
 */
export function usePreferences(): Preferences {
  const [prefs, setPrefs] = useState<Preferences>(cache ?? DEFAUTS);

  useEffect(() => {
    const sync = () => setPrefs({ ...(cache ?? DEFAUTS) });
    abonnes.add(sync);
    if (!cache) void charger();
    return () => { abonnes.delete(sync); };
  }, []);

  return prefs;
}

/** Modifie une préférence et la persiste immédiatement. */
export function useDefinirPreference() {
  return useCallback(async <K extends keyof Preferences>(cle: K, valeur: Preferences[K]) => {
    cache = { ...(cache ?? DEFAUTS), [cle]: valeur };
    notifier();
    await kv.set(CLES_KV.preferences, cache);
  }, []);
}

/** Lit la valeur courante sans abonnement (utile dans les callbacks). */
export function lirePreference<K extends keyof Preferences>(cle: K): Preferences[K] {
  return (cache ?? DEFAUTS)[cle];
}
