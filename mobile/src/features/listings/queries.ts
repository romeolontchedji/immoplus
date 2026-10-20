import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import { t } from "@/i18n/fr";
import type { components } from "@/api/genere/api";
import { versParametres, type Filtres } from "./filtres";

export type Fiche = components["schemas"]["FicheOut"];
export type Carte = components["schemas"]["CarteOut"];

export function useDistricts() {
  return useQuery({ queryKey: qk.districts, queryFn: () => unwrap(api.GET("/v1/districts")), staleTime: 24 * 60 * 60_000 });
}

export type TypeChambre = { slug: string; label: string; count?: number };

/** Repli hors ligne : les 4 types officiels (la liste vivante vient du serveur, décision V1). */
export const TYPES_OFFICIELS: TypeChambre[] = Object.entries(t.typeChambre).map(([slug, label]) => ({ slug, label }));

/** Types validés, les plus courants d'abord ; jamais vide (repli sur les officiels). */
export function useTypesChambre(): TypeChambre[] {
  const { data } = useQuery({ queryKey: qk.typesChambre, queryFn: () => unwrap(api.GET("/v1/room-types")), staleTime: 60 * 60_000 });
  return data?.length ? data : TYPES_OFFICIELS;
}

/** Libellé d'un type : liste du serveur, puis officiels, sinon le slug. */
export function libelleType(types: TypeChambre[], slug: string): string {
  return types.find((x) => x.slug === slug)?.label ?? t.typeChambre[slug] ?? slug;
}

/** Chambres similaires (quartier, type, loyer, distance), même source que le site (plan v2, S3). */
export const useSimilaires = (ident: string | undefined) =>
  useQuery({ queryKey: qk.similaires(ident ?? ""), enabled: !!ident, queryFn: () => unwrap(api.GET("/v1/listings/{ident}/similar", { params: { path: { ident: ident as string } } })), staleTime: 5 * 60_000 });

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

export type ListeAvis = components["schemas"]["AvisListeOut"];
export type ProfilGerant = components["schemas"]["GerantPublicOut"];

/** Avis des locataires d'une chambre, et si le locataire connecté peut en donner un (plan v3, G). */
export const useAvis = (ident: string | undefined) =>
  useQuery({ queryKey: qk.avis(ident ?? ""), enabled: !!ident, queryFn: () => unwrap(api.GET("/v1/listings/{ident}/reviews", { params: { path: { ident: ident as string } } })) });

/** Donner, modifier ou retirer son avis ; la fiche et la liste sont relues ensuite. */
export function useMonAvis(ident: string) {
  const qc = useQueryClient();
  const relire = () => {
    void qc.invalidateQueries({ queryKey: qk.avis(ident) });
    void qc.invalidateQueries({ queryKey: qk.fiche(ident) });
  };
  return {
    donner: useMutation({
      mutationFn: (v: { rating: number; comment: string }) => unwrap(api.PUT("/v1/listings/{ident}/my-review", { params: { path: { ident } }, body: v })),
      onSuccess: relire,
    }),
    retirer: useMutation({ mutationFn: () => unwrap(api.DELETE("/v1/listings/{ident}/my-review", { params: { path: { ident } } })), onSuccess: relire }),
  };
}

/** Profil public d'un gérant : chambres en ligne et avis, jamais de numéro (plan v3, F1). */
export const useProfilGerant = (id: string | undefined) =>
  useQuery({ queryKey: qk.gerant(id ?? ""), enabled: !!id, queryFn: () => unwrap(api.GET("/v1/gerants/{gerant_id}", { params: { path: { gerant_id: id as string } } })) });

/** « Contacter le gérant » : ouvre (ou retrouve) la discussion, sans message imposé (plan v3, B6). */
export function useDemarrerConversation() {
  return useMutation({ mutationFn: (annonceId: string) => unwrap(api.POST("/v1/conversations/start", { body: { listing_id: annonceId } })) });
}
