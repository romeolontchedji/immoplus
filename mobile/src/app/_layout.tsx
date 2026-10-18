import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import * as SplashScreen from "expo-splash-screen";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { VerrouHote } from "@/features/auth/verrou";
import { BanniereInterne } from "@/features/notifications/BanniereInterne";
import { AppGate } from "@/features/system/AppGate";
import { FiltresProvider } from "@/features/listings/filtres";
import { DemandeNotificationsHote } from "@/features/notifications/DemandeNotifications";
import { usePushBootstrap } from "@/features/notifications/push";
import { RealtimeProvider } from "@/realtime/RealtimeProvider";
import { outbox } from "@/storage/outbox";
import { PREFIXES_PERSISTES, persister, queryClient } from "@/state/queryClient";
import { SessionProvider, useSession } from "@/state/session";
import { ThemeProvider } from "@/ui/theme/ThemeProvider";
import { DemarrageAnime } from "@/ui/components/DemarrageAnime";
import { POLICES } from "@/ui/theme/polices";

void SplashScreen.preventAutoHideAsync();

/** Ordre des fournisseurs : gestes → zone sûre → thème → cache → session → barrière (mise à jour / maintenance) → temps réel → filtres. */
export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
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
    </GestureHandlerRootView>
  );
}

function Racine() {
  const { etat } = useSession();
  const [policesChargees, erreurPolices] = useFonts(POLICES);
  const pret = etat.statut !== "chargement" && (policesChargees || !!erreurPolices); // sans police : celle du système
  const [animation, setAnimation] = useState(true); // logo animé une fois par lancement, après l'écran natif
  const finAnimation = useCallback(() => setAnimation(false), []);
  usePushBootstrap();
  useEffect(() => void outbox.precharger(), []);
  useEffect(() => {
    if (pret) void SplashScreen.hideAsync(); // l'écran de démarrage reste tant que la session et la police ne sont pas prêtes
  }, [pret]);
  return (
    <>
      <Stack screenOptions={{ headerShown: false }} />
      <DemandeNotificationsHote />
      <BanniereInterne />
      <VerrouHote />
      {animation && pret ? <DemarrageAnime onFin={finAnimation} /> : null}
    </>
  );
}
