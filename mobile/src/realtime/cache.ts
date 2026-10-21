import { qk } from "@/api/keys";
import { appliquerModeration, fusionner, type HistoriqueLocal } from "@/lib/messages";
import { queryClient } from "@/state/queryClient";
import { annoncerNotification } from "@/features/notifications/annonces";
import type { EvenementServeur } from "./events";

/** Met à jour le cache TanStack à partir d'un événement serveur (la source de vérité reste l'API HTTP). */
export function appliquerEvenement(e: EvenementServeur): void {
  switch (e.type) {
    case "message.new": {
      const { conversation_id: id, message } = e.data;
      queryClient.setQueryData<HistoriqueLocal>(qk.messages(id), (h?: HistoriqueLocal) =>
        h ? { ...h, items: fusionner(h.items, [message]), dernierSeq: Math.max(h.dernierSeq, message.seq) } : h,
      );
      void queryClient.invalidateQueries({ queryKey: qk.conversations });
      void queryClient.invalidateQueries({ queryKey: qk.conversation(id) });
      break;
    }
    case "message.moderated":
      queryClient.setQueryData<HistoriqueLocal>(qk.messages(e.data.conversation_id), (h?: HistoriqueLocal) =>
        h ? { ...h, items: appliquerModeration(h.items, e.data.message_id, e.data.moderation_status) } : h,
      );
      break;
    case "conversation.read":
    case "conversation.updated":
      void queryClient.invalidateQueries({ queryKey: qk.conversation(e.data.conversation_id) });
      void queryClient.invalidateQueries({ queryKey: qk.conversations });
      break;
    case "notification.new":
      annoncerNotification(e.data.notification);
      queryClient.setQueryData(qk.nonLues, { unread_count: e.data.unread_count });
      void queryClient.invalidateQueries({ queryKey: qk.notifications });
      break;
    default:
      break;
  }
}
