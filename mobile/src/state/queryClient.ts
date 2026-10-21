import { QueryClient, onlineManager } from "@tanstack/react-query";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import AsyncStorage from "@react-native-async-storage/async-storage";
import NetInfo from "@react-native-community/netinfo";
import { isApiError, isRetryable } from "@/api/errors";
import { CLES_KV } from "@/storage/kv";

/** Le gestionnaire de connexion de TanStack suit NetInfo : les requêtes se suspendent hors ligne et reprennent au retour du réseau. */
onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((etat) => setOnline(etat.isConnected !== false && etat.isInternetReachable !== false)),
);

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 24 * 60 * 60 * 1000, // 24 h : le cache persisté sert de « dernier fil » hors connexion (ENF-RES-01)
      // Pas de nouvelle tentative pour une erreur métier (4xx) ; trois pour le réseau et les 5xx.
      retry: (tentative, erreur) => isRetryable(erreur) && tentative < 3,
      retryDelay: (tentative) => Math.min(1000 * 2 ** tentative, 15_000),
      refetchOnReconnect: true,
    },
    mutations: { retry: false },
  },
});

export const persister = createAsyncStoragePersister({ storage: AsyncStorage, key: CLES_KV.cacheRequetes, throttleTime: 2000 });

/** Seules les lectures publiques sont persistées : jamais de messages ni de données personnelles sur le disque en clair. */
export const PREFIXES_PERSISTES = new Set(["fil", "fiche", "districts", "types-chambre", "app-config"]);

export function estSessionPerdue(erreur: unknown): boolean {
  return isApiError(erreur) && erreur.status === 401;
}
