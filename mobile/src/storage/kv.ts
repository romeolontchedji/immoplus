import AsyncStorage from "@react-native-async-storage/async-storage";

/** Données non secrètes persistées en JSON : préférences, brouillon d'annonce, file d'envoi, cache des requêtes. */
export const kv = {
  async get<T>(cle: string): Promise<T | null> {
    const brut = await AsyncStorage.getItem(cle);
    if (brut === null) return null;
    try {
      return JSON.parse(brut) as T;
    } catch {
      await AsyncStorage.removeItem(cle); // contenu corrompu : on repart de zéro plutôt que de planter
      return null;
    }
  },
  async set(cle: string, valeur: unknown): Promise<void> {
    await AsyncStorage.setItem(cle, JSON.stringify(valeur));
  },
  async remove(cle: string): Promise<void> {
    await AsyncStorage.removeItem(cle);
  },
};

export const CLES_KV = {
  preferences: "logeo.preferences",
  brouillon: "logeo.brouillon-annonce",
  outbox: "logeo.outbox",
  cacheRequetes: "logeo.cache-requetes",
  onboardingVu: "logeo.onboarding-vu",
} as const;
