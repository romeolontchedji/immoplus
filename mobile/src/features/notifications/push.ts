import { useEffect } from "react";
import { Platform } from "react-native";
import { isRunningInExpoGo } from "expo";
import * as Device from "expo-device";
import type * as Notifications from "expo-notifications";
import { useRouter } from "expo-router";
import { api, unwrap } from "@/api/client";
import { EAS_PROJECT_ID } from "@/config/env";
import { focusActuel } from "@/realtime/focus";
import { useSession } from "@/state/session";
import { destination } from "./routage";

type ModuleNotifications = typeof import("expo-notifications");

/**
 * Sous Expo Go Android, le simple import de `expo-notifications` lève une erreur depuis le SDK 53
 * (enregistrement automatique du jeton au chargement du module) : cela faisait échouer `_layout.tsx`
 * et les routes qui importent ce fichier. On charge donc le module à la demande, jamais sous Expo Go.
 * Le push distant exige un dev build / EAS.
 */
let moduleNotifications: Promise<ModuleNotifications | null> | null = null;

async function chargerNotifications(): Promise<ModuleNotifications | null> {
  if (isRunningInExpoGo()) return null;
  moduleNotifications ??= Promise.resolve()
    .then(() => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const notifs = require("expo-notifications") as ModuleNotifications;
        // Au premier plan : bannière et son, sauf pour la conversation déjà à l'écran.
        notifs.setNotificationHandler({
          handleNotification: async (n) => {
            const data = n.request.content.data as { kind?: string; conversation_id?: string } | undefined;
            const dejaALEcran = data?.kind === "message.received" && data.conversation_id === focusActuel();
            return { shouldShowBanner: !dejaALEcran, shouldShowList: !dejaALEcran, shouldPlaySound: !dejaALEcran, shouldSetBadge: false };
          },
        });
        return notifs;
      } catch {
        return null;
      }
    });
  return moduleNotifications;
}

async function creerCanaux(notifs: ModuleNotifications): Promise<void> {
  if (Platform.OS !== "android") return;
  await notifs.setNotificationChannelAsync("messages", { name: "Messages", importance: notifs.AndroidImportance.HIGH, vibrationPattern: [0, 200, 100, 200] });
  await notifs.setNotificationChannelAsync("alertes", { name: "Alertes et favoris", importance: notifs.AndroidImportance.DEFAULT });
  await notifs.setNotificationChannelAsync("rappels", { name: "Rappels", importance: notifs.AndroidImportance.LOW });
}

/** Demande l'autorisation (à appeler au bon moment : après la première conversation, ou depuis les préférences) puis enregistre le jeton. */
export async function activerPush(): Promise<"actif" | "refuse" | "indisponible"> {
  const notifs = await chargerNotifications();
  if (!notifs) return "indisponible"; // Expo Go : push distant retiré (SDK 53+)
  if (!Device.isDevice) return "indisponible"; // pas de push sur émulateur
  await creerCanaux(notifs);
  let { status } = await notifs.getPermissionsAsync();
  if (status !== "granted") ({ status } = await notifs.requestPermissionsAsync());
  if (status !== "granted") return "refuse";
  const { data: token } = await notifs.getExpoPushTokenAsync(EAS_PROJECT_ID ? { projectId: EAS_PROJECT_ID } : undefined);
  await unwrap(api.PUT("/v1/devices/current/push-token", { body: { provider: "expo", token } }));
  return "actif";
}

/**
 * Tant qu'une session est ouverte : renouvelle le jeton si l'autorisation est déjà accordée (le jeton peut changer) et
 * route les appuis sur une notification, y compris celle qui a lancé l'application à froid.
 */
export function usePushBootstrap(): void {
  const { etat, role } = useSession();
  const router = useRouter();
  const connecte = etat.statut === "connecte";

  useEffect(() => {
    if (!connecte) return;
    let annule = false;
    void chargerNotifications().then(async (notifs) => {
      if (!notifs || annule) return;
      const { status } = await notifs.getPermissionsAsync();
      if (status === "granted") await activerPush().catch(() => undefined);
    });
    return () => {
      annule = true;
    };
  }, [connecte]);

  useEffect(() => {
    if (!connecte) return;
    let annule = false;
    let abonnement: { remove(): void } | undefined;
    void chargerNotifications().then((notifs) => {
      if (!notifs || annule) return;
      const aller = (r: Notifications.NotificationResponse | null) => {
        if (!r) return;
        const contenu = r.notification.request.content.data as Record<string, unknown>;
        router.push(destination(contenu.kind as string | undefined, contenu, role));
      };
      aller(notifs.getLastNotificationResponse());
      abonnement = notifs.addNotificationResponseReceivedListener(aller);
    });
    return () => {
      annule = true;
      abonnement?.remove();
    };
  }, [connecte, role, router]);
}
