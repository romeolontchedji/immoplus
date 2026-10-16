import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import type { components } from "@/api/genere/api";
import { versParametres, type Filtres } from "./filtres";

export type Fiche = components["schemas"]["FicheOut"];
export type Carte = components["schemas"]["CarteOut"];

export function useDistricts() {
  return useQuery({ queryKey: qk.districts, queryFn: () => unwrap(api.GET("/v1/districts")), staleTime: 24 * 60 * 60_000 });
}

/** Fil et recherche : pagination par curseur opaque (`next_cursor`), 10 cartes par page. */
export function useFil(filtres: Filtres) {
  return useInfiniteQuery({
    queryKey: qk.fil(filtres),
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => unwrap(api.GET("/v1/listings", { params: { query: versParametres(filtres, pageParam) } })),
    getNextPageParam: (derniere) => derniere.next_cursor ?? undefined,
  });
}

export function useFiche(ident: string | undefined) {
  return useQuery({
    queryKey: qk.fiche(ident ?? ""),
    queryFn: () => unwrap(api.GET("/v1/listings/{ident}", { params: { path: { ident: ident as string } } })),
    enabled: !!ident,
  });
}

/** Compte une vue (une par visiteur et par jour côté serveur). Silencieux : un échec n'est jamais montré. */
export function useCompterVue() {
  return useMutation({ mutationFn: (ident: string) => unwrap(api.POST("/v1/listings/{ident}/views", { params: { path: { ident } } })) });
}

export function useFavoris(actif = true) {
  return useQuery({ queryKey: qk.favoris, queryFn: () => unwrap(api.GET("/v1/me/favorites")), enabled: actif });
}

/** Ajout/retrait optimiste : l'icône réagit tout de suite, le cache revient en arrière si le serveur refuse. */
export function useBasculerFavori() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ident, actif }: { id: string; ident: string; actif: boolean }) => {
      if (actif) await unwrap(api.PUT("/v1/me/favorites/{annonce_id}", { params: { path: { annonce_id: id } } }));
      else await unwrap(api.DELETE("/v1/me/favorites/{annonce_id}", { params: { path: { annonce_id: id } } }));
      return ident;
    },
    onMutate: async ({ ident, actif }) => {
      await qc.cancelQueries({ queryKey: qk.fiche(ident) });
      const avant = qc.getQueryData<Fiche>(qk.fiche(ident));
      if (avant) qc.setQueryData<Fiche>(qk.fiche(ident), { ...avant, is_favorite: actif });
      return { avant, ident };
    },
    onError: (_e, _v, ctx) => ctx?.avant && qc.setQueryData(qk.fiche(ctx.ident), ctx.avant),
    onSettled: () => void qc.invalidateQueries({ queryKey: qk.favoris }),
  });
}

export function useSignaler() {
  return useMutation({
    mutationFn: (v: { cible: "listing" | "message" | "conversation" | "user"; id: string; motif: components["schemas"]["SignalementIn"]["reason_code"]; details?: string }) =>
      unwrap(api.POST("/v1/reports", { body: { target_type: v.cible, target_id: v.id, reason_code: v.motif, details: v.details ?? "" } })),
  });
}

export function useSignalerDejaLouee() {
  return useMutation({ mutationFn: (annonceId: string) => unwrap(api.POST("/v1/listings/{annonce_id}/report-rented", { params: { path: { annonce_id: annonceId } } })) });
}
