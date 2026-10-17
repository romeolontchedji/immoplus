import { useCallback, useEffect, useMemo, useSyncExternalStore } from "react";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { isApiError, isRetryable } from "@/api/errors";
import { qk } from "@/api/keys";
import { composerLignes, fusionner, type HistoriqueLocal, type LigneAffichee } from "@/lib/messages";
import { newId } from "@/lib/uuid";
import { outbox, type ElementFile } from "@/storage/outbox";
import { useOnline } from "@/hooks/useOnline";

/** Liste des conversations (locataire ou gérant, selon le jeton) : 30 par page, curseur = date du dernier message. */
export function useConversations(annonceId?: string) {
  return useInfiniteQuery({
    queryKey: [...qk.conversations, annonceId ?? null],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => unwrap(api.GET("/v1/conversations", { params: { query: { cursor: pageParam, listing: annonceId } } })),
    getNextPageParam: (p) => p.next_cursor ?? undefined,
  });
}

export function useConversation(id: string | undefined) {
  return useQuery({ queryKey: qk.conversation(id ?? ""), queryFn: () => unwrap(api.GET("/v1/conversations/{conversation_id}", { params: { path: { conversation_id: id as string } } })), enabled: !!id });
}

/** Dernière page de messages ; les plus anciens se chargent à la demande (`chargerPlusAnciens`, `before_seq`). */
export function useMessages(id: string | undefined) {
  const qc = useQueryClient();
  return {
    ...useQuery<HistoriqueLocal>({
      queryKey: qk.messages(id ?? ""),
      enabled: !!id,
      queryFn: async () => {
        const dejaLa = qc.getQueryData<HistoriqueLocal>(qk.messages(id as string));
        // Rattrapage : si on a déjà un historique, on ne demande que ce qui suit (`after_seq`) ; sinon la dernière page.
        const r = await unwrap(api.GET("/v1/conversations/{conversation_id}/messages", { params: { path: { conversation_id: id as string }, query: dejaLa ? { after_seq: dejaLa.dernierSeq } : {} } }));
        if (dejaLa) return { items: fusionner(dejaLa.items, r.items), plusAnciens: dejaLa.plusAnciens, dernierSeq: r.last_seq };
        return { items: r.items, plusAnciens: r.has_more, dernierSeq: r.last_seq };
      },
    }),
    chargerPlusAnciens: async () => {
      const h = qc.getQueryData<HistoriqueLocal>(qk.messages(id as string));
      const premier = h?.items[0];
      if (!h || !premier || !h.plusAnciens) return;
      const r = await unwrap(api.GET("/v1/conversations/{conversation_id}/messages", { params: { path: { conversation_id: id as string }, query: { before_seq: premier.seq } } }));
      qc.setQueryData<HistoriqueLocal>(qk.messages(id as string), { ...h, items: fusionner(r.items, h.items), plusAnciens: r.has_more });
    },
  };
}

/** Envoie un message du service `outbox` : POST idempotent (même `client_msg_id`) → jamais de doublon, même après un envoi « incertain ». */
async function posterMessage(e: ElementFile): Promise<void> {
  await unwrap(api.POST("/v1/conversations/{conversation_id}/messages", { params: { path: { conversation_id: e.conversationId } }, body: { body: e.body, client_msg_id: e.clientMsgId } }));
}

export const classerErreur = (erreur: unknown) => ({ reessayer: isRetryable(erreur), code: isApiError(erreur) ? erreur.code : undefined });

/** Contenu de la file d'envoi (réactif) pour une conversation. */
export function useFileDEnvoi(conversationId: string | undefined): ElementFile[] {
  const toutes = useSyncExternalStore(outbox.abonner, outbox.instantane);
  return useMemo(() => toutes.filter((e) => e.conversationId === conversationId), [toutes, conversationId]);
}

/** Vide la file d'envoi de la conversation et rafraîchit l'historique. Reprise automatique au retour du réseau (ENF-RES-02). */
export function useReprendreEnvoi(conversationId: string | undefined) {
  const qc = useQueryClient();
  const enLigne = useOnline();
  const reprendre = useCallback(async () => {
    await outbox.envoyerTout(posterMessage, classerErreur);
    if (conversationId) void qc.invalidateQueries({ queryKey: qk.messages(conversationId) });
    void qc.invalidateQueries({ queryKey: qk.conversations });
  }, [qc, conversationId]);
  useEffect(() => {
    if (enLigne) void reprendre();
  }, [enLigne, reprendre]);
  return reprendre;
}

/** Envoi d'un message : écrit d'abord dans la file (affichage immédiat « en attente »), puis tente l'envoi. */
export function useEnvoyerMessage(conversationId: string | undefined) {
  const reprendre = useReprendreEnvoi(conversationId);
  return useMutation({
    mutationFn: async (body: string) => {
      const texte = body.trim();
      if (!conversationId || !texte) return; // jamais de message vide dans la file
      await outbox.ajouter({ clientMsgId: newId(), conversationId, body: texte });
      await reprendre();
    },
  });
}

export function useLireConversation(conversationId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (upToSeq: number) => unwrap(api.POST("/v1/conversations/{conversation_id}/read", { params: { path: { conversation_id: conversationId as string } }, body: { up_to_seq: upToSeq } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.conversations }),
  });
}

export function useBloquer(conversationId: string, bloquer: boolean) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => bloquer
      ? unwrap(api.POST("/v1/conversations/{conversation_id}/block", { params: { path: { conversation_id: conversationId } } }))
      : unwrap(api.POST("/v1/conversations/{conversation_id}/unblock", { params: { path: { conversation_id: conversationId } } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.conversation(conversationId) }),
  });
}

/** Sourdine : jusqu'à une date (8 h, 1 semaine, « toujours » = 10 ans), ou `null` pour réactiver. */
export function useSourdine(conversationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jusqua: Date | null) =>
      unwrap(api.PATCH("/v1/conversations/{conversation_id}", { params: { path: { conversation_id: conversationId } }, body: { muted_until: jusqua ? jusqua.toISOString() : null } })),
    onSuccess: () => void Promise.all([qc.invalidateQueries({ queryKey: qk.conversation(conversationId) }), qc.invalidateQueries({ queryKey: qk.conversations })]),
  });
}

/** Première prise de contact : ouvre la conversation de l'annonce et envoie le premier message (idempotent). */
export function useOuvrirConversation() {
  return useMutation({
    mutationFn: (v: { listingId: string; body: string }) => unwrap(api.POST("/v1/conversations", { body: { listing_id: v.listingId, body: v.body.trim(), client_msg_id: newId() } })),
  });
}

export function useLignes(conversationId: string | undefined, moi: string, lectureAutre: number, serveur: HistoriqueLocal | undefined): LigneAffichee[] {
  const file = useFileDEnvoi(conversationId);
  return useMemo(() => composerLignes(serveur?.items ?? [], file, moi, lectureAutre), [serveur, file, moi, lectureAutre]);
}
