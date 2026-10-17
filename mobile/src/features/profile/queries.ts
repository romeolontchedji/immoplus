import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import type { components } from "@/api/genere/api";
import type { Occupation } from "@/features/auth/ChoixOccupation";
import { useSession } from "@/state/session";

export type Appareil = components["schemas"]["AppareilOut"];
export type PreferencesNotif = { messages: boolean; apercu: boolean; alertes: boolean; rappels: boolean };

/** Profil courant (cache court : rafraîchi à l'ouverture de l'écran). */
export const useMe = () => useQuery({ queryKey: qk.me, queryFn: () => unwrap(api.GET("/v1/me")), staleTime: 30_000 });

/** Modifier le nom complet et « Tu es » (`null` efface la réponse). */
export function useModifierProfil() {
  const { rafraichirProfil } = useSession();
  return useMutation({
    mutationFn: (corps: { full_name: string; occupation: Occupation | null }) => unwrap(api.PATCH("/v1/me", { body: corps })),
    onSuccess: () => void rafraichirProfil(),
  });
}

/** Changer le mot de passe (connexion : ancien + nouveau). */
export function useChangerMotDePasse() {
  return useMutation({
    mutationFn: (corps: { current_password: string; new_password: string }) =>
      unwrap(api.POST("/v1/auth/password/change", { body: corps })),
  });
}

/** Finaliser le changement de numéro (après OTP). */
export function useChangerTelephone() {
  const { rafraichirProfil } = useSession();
  return useMutation({
    mutationFn: (corps: { otp_token: string; password: string }) =>
      unwrap(api.POST("/v1/me/phone/change", { body: corps })),
    onSuccess: () => void rafraichirProfil(),
  });
}

/** Liste des appareils connectés. */
export const useAppareils = () =>
  useQuery({ queryKey: qk.appareils, queryFn: () => unwrap(api.GET("/v1/devices")) });

/** Révoquer un appareil à distance. */
export function useRevoquerAppareil() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.DELETE("/v1/devices/{appareil_id}", { params: { path: { appareil_id: id } } })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.appareils }),
  });
}

/**
 * Préférences de notification, au format du serveur (`definir_preferences`) :
 * `{ messages: {push, apercu}, alertes: {push}, rappels: {push} }`. Absent = activé.
 */
type Reglage = { push?: boolean; apercu?: boolean };
type PreferencesServeur = Partial<Record<"messages" | "alertes" | "rappels", Reglage>>;

export const usePreferencesNotif = () =>
  useQuery<PreferencesNotif>({
    queryKey: qk.preferencesNotif,
    queryFn: async () => {
      const brut: PreferencesServeur | undefined = await unwrap(api.GET("/v1/me/preferences"));
      return {
        messages: brut?.messages?.push !== false,
        apercu: brut?.messages?.apercu !== false,
        alertes: brut?.alertes?.push !== false,
        rappels: brut?.rappels?.push !== false,
      };
    },
  });

/** Enregistrer les préférences de notification (seules les catégories envoyées changent côté serveur). */
export function useEnregistrerPreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: PreferencesNotif) => {
      const corps: PreferencesServeur = {
        messages: { push: p.messages, apercu: p.apercu },
        alertes: { push: p.alertes },
        rappels: { push: p.rappels },
      };
      return unwrap(api.PUT("/v1/me/preferences", { body: corps }));
    },
    onMutate: async (p) => {
      await qc.cancelQueries({ queryKey: qk.preferencesNotif });
      const avant = qc.getQueryData<PreferencesNotif>(qk.preferencesNotif);
      qc.setQueryData(qk.preferencesNotif, p); // l'interrupteur réagit tout de suite
      return { avant };
    },
    onError: (_e, _p, ctx) => ctx?.avant && qc.setQueryData(qk.preferencesNotif, ctx.avant),
    onSettled: () => void qc.invalidateQueries({ queryKey: qk.preferencesNotif }),
  });
}

/** Supprimer le compte (irréversible). */
export function useSupprimerCompte() {
  const { fermer } = useSession();
  return useMutation({
    mutationFn: () => unwrap(api.DELETE("/v1/me")),
    onSuccess: () => void fermer(),
  });
}
