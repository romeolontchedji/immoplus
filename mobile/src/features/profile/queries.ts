import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import type { components } from "@/api/genere/api";
import { useSession } from "@/state/session";

export type Appareil = components["schemas"]["AppareilOut"];
export type PreferencesNotif = { messages: boolean; alerts: boolean; reminders: boolean };

/** Profil courant (cache court : rafraîchi à l'ouverture de l'écran). */
export const useMe = () => useQuery({ queryKey: qk.me, queryFn: () => unwrap(api.GET("/v1/me")), staleTime: 30_000 });

/** Modifier le nom complet. */
export function useModifierNom() {
  const { rafraichirProfil } = useSession();
  return useMutation({
    mutationFn: (full_name: string) => unwrap(api.PATCH("/v1/me", { body: { full_name } })),
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

/** Préférences de notification (schéma libre côté serveur). */
export const usePreferencesNotif = () =>
  useQuery<PreferencesNotif>({
    queryKey: qk.preferencesNotif,
    queryFn: async () => {
      const raw = (await unwrap(api.GET("/v1/me/preferences"))) as unknown as Record<string, boolean> | undefined;
      return {
        messages: raw?.["messages"] ?? true,
        alerts: raw?.["alerts"] ?? true,
        reminders: raw?.["reminders"] ?? false,
      };
    },
  });

/** Enregistrer les préférences de notification. */
export function useEnregistrerPreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (corps: PreferencesNotif) =>
      unwrap(api.PUT("/v1/me/preferences", { body: corps as any })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.preferencesNotif }),
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
