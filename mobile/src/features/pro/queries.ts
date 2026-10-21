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
    refetchInterval: (q) => (q.state.data?.some((m) => m.status === "uploaded" || m.status === "processing" || m.status === "pending") ? 3000 : false),
  });

/** Retire une photo ou la vidéo d'une annonce (refusé pour une annonce en ligne qui passerait sous le minimum). */
export function useSupprimerMedia(annonceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mediaId: string) =>
      unwrap(api.DELETE("/v1/pro/listings/{annonce_id}/media/{media_id}", { params: { path: { annonce_id: annonceId as string, media_id: mediaId } } })),
    onSettled: () => void qc.invalidateQueries({ queryKey: qk.pro.medias(annonceId ?? "") }),
  });
}

type Action = "confirm" | "hide" | "mark-rented" | "undo-rented" | "publish";

/** Actions de cycle de vie d'une annonce : confirmer la disponibilité, masquer, marquer louée, annuler, publier. */
export function useActionAnnonce(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (action: Action) => unwrap(api.POST(`/v1/pro/listings/{annonce_id}/${action}`, { params: { path: { annonce_id: id } } })),
    onSuccess: () => void Promise.all([qc.invalidateQueries({ queryKey: qk.pro.annonce(id) }), qc.invalidateQueries({ queryKey: qk.pro.annonces }), qc.invalidateQueries({ queryKey: qk.pro.tableau }), qc.invalidateQueries({ queryKey: qk.pro.preparation(id) })]),
  });
}

/** Ce qui manque pour publier (mêmes libellés que le site). */
export const usePreparation = (id: string | undefined) =>
  useQuery({ queryKey: qk.pro.preparation(id ?? ""), enabled: !!id, queryFn: () => unwrap(api.GET("/v1/pro/listings/{annonce_id}/readiness", { params: { path: { annonce_id: id as string } } })) });

/** Vues, favoris et contacts d'une annonce sur 7 ou 30 jours. */
export const useStatistiques = (id: string | undefined, jours: 7 | 30) =>
  useQuery({ queryKey: qk.pro.stats(id ?? "", jours), enabled: !!id, queryFn: () => unwrap(api.GET("/v1/pro/listings/{annonce_id}/stats", { params: { path: { annonce_id: id as string }, query: { days: jours } } })) });

export type ModificationAnnonce = components["schemas"]["PatchedAnnonceIn"];

/** Modifier une annonce existante (PATCH partiel). */
export function useModifierAnnonce(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (corps: ModificationAnnonce) => unwrap(api.PATCH("/v1/pro/listings/{annonce_id}", { params: { path: { annonce_id: id } }, body: corps })),
    onSuccess: () => void Promise.all([qc.invalidateQueries({ queryKey: qk.pro.annonce(id) }), qc.invalidateQueries({ queryKey: qk.pro.annonces }), qc.invalidateQueries({ queryKey: qk.pro.preparation(id) })]),
  });
}

/** Aperçu Markdown : rendu par le serveur (même moteur que l'affichage public, HTML déjà assaini). */

export type TypeChambrePro = components["schemas"]["TypeChambreProOut"];

/** Types utilisables par le gérant : validés, et ses propositions en attente (décision V1). */
export const useTypesChambrePro = () =>
  useQuery({ queryKey: qk.pro.types, queryFn: () => unwrap(api.GET("/v1/pro/room-types")), staleTime: 5 * 60_000 });

/** Proposer un type : le serveur renvoie l'équivalent existant s'il y en a un. */
export function useProposerType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (label: string) => unwrap(api.POST("/v1/pro/room-types", { body: { label } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.pro.types }),
  });
}

/** Supprime une annonce ou un brouillon (plan v3, C6) : une annonce en ligne est d'abord archivée par le serveur. */
export function useSupprimerAnnonce(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.DELETE("/v1/pro/listings/{annonce_id}", { params: { path: { annonce_id: id } } })),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.pro.annonces });
      void qc.invalidateQueries({ queryKey: qk.pro.tableau });
    },
  });
}
