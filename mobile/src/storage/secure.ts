import * as SecureStore from "expo-secure-store";

/** Secrets de l'appareil : jeton de rafraîchissement et identifiant d'installation. Jamais dans AsyncStorage. */
const CLES = { refresh: "logeo.refresh", installation: "logeo.installation" } as const;

export const secure = {
  async getRefresh(): Promise<string | null> {
    return SecureStore.getItemAsync(CLES.refresh);
  },
  async setRefresh(jeton: string): Promise<void> {
    await SecureStore.setItemAsync(CLES.refresh, jeton, { keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK });
  },
  async clearRefresh(): Promise<void> {
    await SecureStore.deleteItemAsync(CLES.refresh);
  },
  async getInstallation(): Promise<string | null> {
    return SecureStore.getItemAsync(CLES.installation);
  },
  async setInstallation(id: string): Promise<void> {
    await SecureStore.setItemAsync(CLES.installation, id);
  },
};
