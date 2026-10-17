import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import * as SplashScreen from "expo-splash-screen";
import { Stack } from "expo-router";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AppGate } from "@/features/system/AppGate";
import { FiltresProvider } from "@/features/listings/filtres";
import { DemandeNotificationsHote } from "@/features/notifications/DemandeNotifications";
import { usePushBootstrap } from "@/features/notifications/push";
import { RealtimeProvider } from "@/realtime/RealtimeProvider";
import { outbox } from "@/storage/outbox";
import { PREFIXES_PERSISTES, persister, queryClient } from "@/state/queryClient";
import { SessionProvider, useSession } from "@/state/session";
import { ThemeProvider } from "@/ui/theme/ThemeProvider";

void SplashScreen.preventAutoHideAsync();

/** Ordre des fournisseurs : zone sûre → thème → cache → session → barrière (mise à jour / maintenance) → temps réel → filtres. */
export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <PersistQueryClientProvider
          client={queryClient}
          persistOptions={{
            persister,
            maxAge: 24 * 60 * 60 * 1000,
            dehydrateOptions: { shouldDehydrateQuery: (q) => q.state.status === "success" && PREFIXES_PERSISTES.has(String(q.queryKey[0])) },
          }}
        >
          <SessionProvider>
            <AppGate>
              <RealtimeProvider>
                <FiltresProvider>
                  <Racine />
                </FiltresProvider>
              </RealtimeProvider>
            </AppGate>
          </SessionProvider>
        </PersistQueryClientProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

function Racine() {
  const { etat } = useSession();
  usePushBootstrap();
  useEffect(() => void outbox.precharger(), []);
  useEffect(() => {
    if (etat.statut !== "chargement") void SplashScreen.hideAsync(); // l'écran de démarrage reste tant que la session n'est pas connue
  }, [etat.statut]);
  return (
    <>
      <Stack screenOptions={{ headerShown: false }} />
      <DemandeNotificationsHote />
    </>
  );
}
