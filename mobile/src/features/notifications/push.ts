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
            return { shouldShowBanner: !dejaALEcran, shouldShowList: !dejaALEcran, shouldPlaySound: !dejaALEcran, shouldSetBadge: true };
          },
        });
        return notifs;
      } catch {
        return null;
      }
    });
  return moduleNotifications;
}

/**
 * Canaux Android : le serveur choisit le canal de chaque push (`channelId`, apps/notifications/services.py CANAUX).
 * Messages en importance haute : bannière en haut de l'écran, son et vibration, même téléphone en veille.
 */
async function creerCanaux(notifs: ModuleNotifications): Promise<void> {
  if (Platform.OS !== "android") return;
  const prive = notifs.AndroidNotificationVisibility.PRIVATE; // écran verrouillé : pas d'aperçu du contenu
  await notifs.setNotificationChannelAsync("messages", { name: "Messages", description: "Réponses des gérants et des locataires", importance: notifs.AndroidImportance.MAX, vibrationPattern: [0, 200, 100, 200], lightColor: "#1B44D6", lockscreenVisibility: prive, showBadge: true });
  await notifs.setNotificationChannelAsync("alertes", { name: "Alertes et favoris", description: "Nouvelles chambres qui correspondent à tes alertes", importance: notifs.AndroidImportance.HIGH, showBadge: true });
  await notifs.setNotificationChannelAsync("rappels", { name: "Rappels", description: "Disponibilité de tes chambres à confirmer", importance: notifs.AndroidImportance.DEFAULT });
  await notifs.setNotificationChannelAsync("compte", { name: "Compte et annonces", description: "Publication, modération, sécurité du compte", importance: notifs.AndroidImportance.DEFAULT });
}

/** État de l'autorisation sans la demander : `indisponible` sous Expo Go, sur émulateur ou si le module manque. */
export async function etatAutorisation(): Promise<"accordee" | "a_demander" | "refusee" | "indisponible"> {
  const notifs = await chargerNotifications();
  if (!notifs || !Device.isDevice) return "indisponible";
  const { status, canAskAgain } = await notifs.getPermissionsAsync();
  if (status === "granted") return "accordee";
  return canAskAgain ? "a_demander" : "refusee";
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
