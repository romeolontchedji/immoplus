import type { components } from "@/api/genere/api";

export type Message = components["schemas"]["MessageOut"];

/** Contenu du cache d'une conversation : messages en ordre de `seq` croissant. */
export type HistoriqueLocal = { items: Message[]; plusAnciens: boolean; dernierSeq: number };

/** Fusionne sans doublon (par `id`, puis `client_msg_id`) et remet dans l'ordre de `seq`. Les événements temps réel et les réponses HTTP arrivent dans n'importe quel ordre. */
export function fusionner(existants: Message[], nouveaux: Message[]): Message[] {
  const parId = new Map<string, Message>();
  for (const m of [...existants, ...nouveaux]) parId.set(m.id, m); // le plus récent gagne (ex. message modéré)
  const vus = new Set<string>();
  const sortie: Message[] = [];
  for (const m of [...parId.values()].sort((a, b) => a.seq - b.seq)) {
    const cle = `${m.sender_id ?? "systeme"}:${m.client_msg_id}`;
    if (vus.has(cle)) continue;
    vus.add(cle);
    sortie.push(m);
  }
  return sortie;
}

export function appliquerModeration(items: Message[], messageId: string, statut: string): Message[] {
  return items.map((m) => (m.id === messageId ? { ...m, moderation_status: statut } : m));
}

/** Messages à afficher : ceux du serveur, puis ceux de la file d'envoi pas encore confirmés (marqués « en attente » ou « échec »). */
export type LigneAffichee =
  | { type: "serveur"; message: Message; lu: boolean }
  | { type: "local"; clientMsgId: string; body: string; etat: "en_attente" | "echec"; codeErreur?: string; creeLe: number };

export function composerLignes(
  serveur: Message[],
  file: { clientMsgId: string; body: string; etat: "en_attente" | "echec"; codeErreur?: string; creeLe: number }[],
  moi: string,
  lectureAutre: number,
): LigneAffichee[] {
  const confirmes = new Set(serveur.map((m) => m.client_msg_id));
  const lignes: LigneAffichee[] = serveur.map((message) => ({ type: "serveur", message, lu: message.sender_id === moi && message.seq <= lectureAutre }));
  for (const e of file) if (!confirmes.has(e.clientMsgId)) lignes.push({ type: "local", ...e });
  return lignes;
}
