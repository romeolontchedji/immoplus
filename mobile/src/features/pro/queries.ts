import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import type { components } from "@/api/genere/api";

export type AnnoncePro = components["schemas"]["AnnonceProOut"];
export type MediaPro = components["schemas"]["MediaOut"];

export const useTableauDeBord = () => useQuery({ queryKey: qk.pro.tableau, queryFn: () => unwrap(api.GET("/v1/pro/dashboard")) });
export const useMesAnnonces = () => useQuery({ queryKey: qk.pro.annonces, queryFn: () => unwrap(api.GET("/v1/pro/listings")) });
export const useAnnoncePro = (id: string | undefined) =>
  useQuery({ queryKey: qk.pro.annonce(id ?? ""), enabled: !!id, queryFn: () => unwrap(api.GET("/v1/pro/listings/{annonce_id}", { params: { path: { annonce_id: id as string } } })) });
export const useMediasPro = (id: string | undefined) =>
  useQuery({
    queryKey: qk.pro.medias(id ?? ""), enabled: !!id,
    queryFn: () => unwrap(api.GET("/v1/pro/listings/{annonce_id}/media", { params: { path: { annonce_id: id as string } } })),
    // Tant qu'un média est en traitement (vidéo : transcodage), on relit toutes les 3 s.
    refetchInterval: (q) => (q.state.data?.some((m) => m.status === "uploading" || m.status === "processing" || m.status === "pending") ? 3000 : false),
  });

type Action = "confirm" | "hide" | "mark-rented" | "undo-rented" | "publish";

/** Actions de cycle de vie d'une annonce : confirmer la disponibilité, masquer, marquer louée, annuler, publier. */
export function useActionAnnonce(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (action: Action) => unwrap(api.POST(`/v1/pro/listings/{annonce_id}/${action}`, { params: { path: { annonce_id: id } } })),
    onSuccess: () => void Promise.all([qc.invalidateQueries({ queryKey: qk.pro.annonce(id) }), qc.invalidateQueries({ queryKey: qk.pro.annonces }), qc.invalidateQueries({ queryKey: qk.pro.tableau })]),
  });
}

/** Aperçu Markdown : rendu par le serveur (même moteur que l'affichage public, HTML déjà assaini). */
export const useApercuMarkdown = () => useMutation({ mutationFn: (markdown: string) => unwrap(api.POST("/v1/pro/markdown/preview", { body: { markdown } })) });
