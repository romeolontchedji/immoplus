import type * as Notifications from "expo-notifications";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import { newId } from "@/lib/uuid";
import { classerErreur, posterMessage } from "@/features/messaging/queries";
import { queryClient } from "@/state/queryClient";
import { outbox } from "@/storage/outbox";

type ModuleNotifications = typeof import("expo-notifications");

/** Catégorie envoyée par le serveur pour les messages (`categoryId`, apps/notifications/services.py). */
export const CATEGORIE_MESSAGE = "message";
export const ACTION_REPONDRE = "repondre";
export const ACTION_LU = "lu";

/** Boutons sous une notification de message : « Répondre » (champ texte) et « Marquer comme lu » (plan v2, N3). */
export async function definirCategories(notifs: ModuleNotifications): Promise<void> {
  await notifs.setNotificationCategoryAsync(CATEGORIE_MESSAGE, [
    { identifier: ACTION_REPONDRE, buttonTitle: "Répondre", textInput: { submitButtonTitle: "Envoyer", placeholder: "Ta réponse…" }, options: { opensAppToForeground: false } },
    { identifier: ACTION_LU, buttonTitle: "Marquer comme lu", options: { opensAppToForeground: false } },
  ]);
}

async function lire(conversationId: string, seq: number | undefined): Promise<void> {
  if (!seq) return;
  await unwrap(api.POST("/v1/conversations/{conversation_id}/read", { params: { path: { conversation_id: conversationId } }, body: { up_to_seq: seq } }));
}

/**
 * Traite un bouton d'action ; renvoie vrai s'il a été géré (pas de navigation). La réponse passe par la file d'envoi
 * (`outbox`) : elle part même avec un réseau instable, sans doublon (identifiant client).
 */
export async function traiterAction(notifs: ModuleNotifications, r: Notifications.NotificationResponse): Promise<boolean> {
  if (r.actionIdentifier !== ACTION_REPONDRE && r.actionIdentifier !== ACTION_LU) return false;
  const data = r.notification.request.content.data as { conversation_id?: string; seq?: number };
  const conversationId = data?.conversation_id;
  if (!conversationId) return true;
  try {
    if (r.actionIdentifier === ACTION_REPONDRE && r.userText?.trim()) {
      await outbox.ajouter({ clientMsgId: newId(), conversationId, body: r.userText.trim() });
      await outbox.envoyerTout(posterMessage, classerErreur);
    }
    await lire(conversationId, data.seq);
  } finally {
    await notifs.dismissNotificationAsync(r.notification.request.identifier).catch(() => undefined);
    void queryClient.invalidateQueries({ queryKey: qk.conversations });
    void queryClient.invalidateQueries({ queryKey: qk.messages(conversationId) });
  }
  return true;
}
