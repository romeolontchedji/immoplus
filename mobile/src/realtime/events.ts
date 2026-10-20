import type { components } from "@/api/genere/api";

/** Événements poussés par le serveur sur le WebSocket (docs/mobile/websocket.md). Un type inconnu est ignoré, jamais une erreur. */
export type Message = components["schemas"]["MessageOut"];
export type Notification = components["schemas"]["NotificationOut"];

export type EvenementServeur =
  | { type: "pong"; data: Record<string, never> }
  | { type: "message.new"; data: { conversation_id: string; message: Message } }
  | { type: "message.moderated"; data: { conversation_id: string; message_id: string; seq: number; moderation_status: string } }
  | { type: "conversation.read"; data: { conversation_id: string; by: string; up_to_seq: number } }
  | { type: "conversation.updated"; data: { conversation_id: string; status: string; blocked_by: string | null } }
  | { type: "notification.new"; data: { unread_count: number; notification: Notification } }
  | { type: "error"; data: { code: string | number } };

const CONNUS = new Set(["pong", "message.new", "message.moderated", "conversation.read", "conversation.updated", "notification.new", "error"]);

export function analyser(texte: string): EvenementServeur | null {
  try {
    const brut = JSON.parse(texte) as { type?: unknown; data?: unknown };
    if (typeof brut.type !== "string" || !CONNUS.has(brut.type)) return null;
    return { type: brut.type, data: brut.data ?? {} } as EvenementServeur;
  } catch {
    return null;
  }
}

/** Codes de fermeture propres à Immo+ (docs/mobile/websocket.md). */
export const FERMETURE = { ticketInvalide: 4401, compteSuspendu: 4403, inactif: 4408, tropDEvenements: 4429, trameTropGrosse: 1009 } as const;
