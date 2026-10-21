import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Platform } from "react-native";
import * as Device from "expo-device";
import { api, unwrap } from "@/api/client";
import type { components } from "@/api/genere/api";
import { apiEvents } from "@/api/events";
import { clearSession, hasRefreshToken, refreshTokens, storeTokens } from "@/api/session";
import { isNetworkError } from "@/api/errors";
import { outbox } from "@/storage/outbox";
import { queryClient } from "./queryClient";

export type Utilisateur = components["schemas"]["UtilisateurOut"];
type Authentification = { user: Utilisateur; tokens: { access: string; refresh: string }; device_id: string };

type Etat =
  | { statut: "chargement" }
  | { statut: "deconnecte" }
  | { statut: "connecte"; user: Utilisateur };

type Valeur = {
  etat: Etat;
  role: "client" | "gerant" | null;
  /** À appeler avec la réponse de login ou register. */
  ouvrir: (reponse: Authentification) => Promise<void>;
  fermer: () => Promise<void>;
  rafraichirProfil: () => Promise<void>;
};

const Ctx = createContext<Valeur | null>(null);

/** `platform` envoyé à l'API à la connexion ; `label` aide l'utilisateur à reconnaître l'appareil dans « Mes appareils ». */
export const IDENTITE_APPAREIL = {
  platform: (Platform.OS === "ios" ? "ios" : "android") as "ios" | "android",
  label: [Device.manufacturer, Device.modelName].filter(Boolean).join(" ") || "Appareil",
};

export function SessionProvider({ children }: { children: ReactNode }) {
  const [etat, setEtat] = useState<Etat>({ statut: "chargement" });

  const charger = useCallback(async () => {
    if (!(await hasRefreshToken())) return setEtat({ statut: "deconnecte" });
    try {
      if (!(await refreshTokens())) return setEtat({ statut: "deconnecte" });
      setEtat({ statut: "connecte", user: await unwrap(api.GET("/v1/me")) });
    } catch (e) {
      // Réseau coupé au démarrage : on garde la session (le jeton est valide) et on réessaiera ; sans profil on ne peut pas choisir l'espace.
      setEtat(isNetworkError(e) ? { statut: "chargement" } : { statut: "deconnecte" });
    }
  }, []);

  useEffect(() => {
    // Amorçage au montage : la session se lit une fois depuis le coffre sécurisé (état externe), c'est le cas d'usage d'un effet.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void charger();
    return apiEvents.on("signed_out", () => {
      queryClient.clear();
      setEtat({ statut: "deconnecte" });
    });
  }, [charger]);

  const ouvrir = useCallback<Valeur["ouvrir"]>(async (r) => {
    await storeTokens(r.tokens);
    queryClient.clear();
    setEtat({ statut: "connecte", user: r.user });
  }, []);

  const fermer = useCallback(async () => {
    try {
      await unwrap(api.POST("/v1/auth/logout"));
    } catch {
      // Hors ligne ou déjà expiré : on ferme quand même localement, c'est l'essentiel.
    }
    await clearSession();
    await outbox.vider(); // aucun message d'un compte ne doit partir depuis un autre
    queryClient.clear();
    setEtat({ statut: "deconnecte" });
  }, []);

  const rafraichirProfil = useCallback(async () => {
    setEtat({ statut: "connecte", user: await unwrap(api.GET("/v1/me")) });
  }, []);

  const valeur = useMemo<Valeur>(
    () => ({ etat, role: etat.statut === "connecte" ? etat.user.role : null, ouvrir, fermer, rafraichirProfil }),
    [etat, ouvrir, fermer, rafraichirProfil],
  );
  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

export function useSession(): Valeur {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession doit être utilisé dans <SessionProvider>.");
  return v;
}
