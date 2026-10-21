import { useCallback, useEffect, useState } from "react";
import { CLES_KV, kv } from "@/storage/kv";

/** Préférences locales de l'appareil (non synchronisées). */
export type Preferences = {
  /** Économie de données : la vidéo de la carte ne se lit qu'à l'appui, jamais automatiquement (CDC §12.2). */
  economieDeDonnees: boolean;
};
const DEFAUT: Preferences = { economieDeDonnees: false };

let cache: Preferences | null = null;
const ecouteurs = new Set<(p: Preferences) => void>();

async function charger(): Promise<Preferences> {
  if (!cache) cache = { ...DEFAUT, ...((await kv.get<Partial<Preferences>>(CLES_KV.preferences)) ?? {}) };
  return cache;
}

export function usePreferences(): [Preferences, (modif: Partial<Preferences>) => Promise<void>] {
  const [prefs, setPrefs] = useState<Preferences>(cache ?? DEFAUT);
  useEffect(() => {
    void charger().then(setPrefs);
    ecouteurs.add(setPrefs);
    return () => void ecouteurs.delete(setPrefs);
  }, []);
  const modifier = useCallback(async (modif: Partial<Preferences>) => {
    const suivant = { ...(await charger()), ...modif };
    cache = suivant;
    await kv.set(CLES_KV.preferences, suivant);
    ecouteurs.forEach((e) => e(suivant));
  }, []);
  return [prefs, modifier];
}

/** Pour les tests. */
export function _reinitialiserPreferences(): void {
  cache = null;
  ecouteurs.clear();
}
