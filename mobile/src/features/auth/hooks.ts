import type { Occupation } from "./ChoixOccupation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { IDENTITE_APPAREIL, useSession } from "@/state/session";
import { montrerCle } from "./cleSecours";

/**
 * Les mutations d'authentification partent toujours : si NetInfo se trompe sur l'accès à Internet (wifi local sans
 * sortie), TanStack les mettrait en pause sans fin. Une vraie coupure remonte en `NetworkError` affichée à l'écran.
 */
const TOUJOURS = { networkMode: "always" } as const;

/** Connexion par nom d'utilisateur et mot de passe (ADR 0009 : plus aucun numéro de téléphone). */
export function useConnexion() {
  const { ouvrir } = useSession();
  return useMutation({
    ...TOUJOURS,
    mutationFn: async ({ username, password }: { username: string; password: string }) => {
      const r = await unwrap(api.POST("/v1/auth/login", { body: { ...IDENTITE_APPAREIL, username: username.trim(), password } }));
      await ouvrir(r);
      return r.user;
    },
  });
}

export type Inscription = { first_name: string; last_name: string; username: string; password: string; occupation: Occupation | null };

/** Inscription sur un seul écran, sans code : la clé de secours s'affiche juste après, une seule fois. */
export function useInscription() {
  const { ouvrir } = useSession();
  return useMutation({
    ...TOUJOURS,
    mutationFn: async (v: Inscription) => {
      const r = await unwrap(api.POST("/v1/auth/register", { body: { ...IDENTITE_APPAREIL, ...v, terms_accepted: true } }));
      montrerCle(r.recovery_key, "inscription");
      await ouvrir(r);
    },
  });
}

/** Le nom d'utilisateur est-il libre ? Vérifié pendant la frappe, avec des suggestions tirées du prénom et du nom. */
export function useDisponibilite(username: string, prenom: string, nom: string) {
  return useQuery({
    queryKey: ["auth", "disponibilite", username, prenom, nom],
    queryFn: () => unwrap(api.GET("/v1/auth/username-available", { params: { query: { username, first_name: prenom, last_name: nom } } })),
    enabled: username.length >= 3,
    staleTime: 10_000,
    placeholderData: (precedent) => precedent,
  });
}

/** Mot de passe oublié, première porte : un lien par e-mail (réponse identique que le compte existe ou non). */
export function useLienParEmail() {
  return useMutation({
    ...TOUJOURS,
    mutationFn: async (identifier: string) => {
      await unwrap(api.POST("/v1/auth/password/email-link", { body: { identifier: identifier.trim() } }));
    },
  });
}

/** Mot de passe oublié, deuxième porte : la clé de secours ; une nouvelle clé la remplace et s'affiche une fois. */
export function useCleDeSecours() {
  return useMutation({
    ...TOUJOURS,
    mutationFn: async (v: { username: string; recovery_key: string; new_password: string }) => {
      const r = await unwrap(api.POST("/v1/auth/password/recovery-key", { body: v }));
      montrerCle(r.recovery_key, "renouvelee");
    },
  });
}
