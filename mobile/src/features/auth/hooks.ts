import { useMutation } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { versE164 } from "@/lib/phone";
import { IDENTITE_APPAREIL, useSession } from "@/state/session";

export type Objet = "signup" | "reset_password" | "change_phone";

/** Étape 1 : demande d'un code SMS. Retourne le délai avant de pouvoir en redemander un. */
export function useDemanderCode(objet: Objet) {
  return useMutation({
    mutationFn: async (saisie: string) => {
      const phone = versE164(saisie);
      if (!phone) throw new Error("numero_invalide");
      const r = await unwrap(api.POST("/v1/auth/otp/request", { body: { phone, purpose: objet } }));
      return { phone, resendAfterS: r.resend_after_s };
    },
  });
}

/** Étape 2 : vérification du code ; rend le jeton à usage unique que consomme l'étape finale. */
export function useVerifierCode(objet: Objet) {
  return useMutation({
    mutationFn: async ({ phone, code }: { phone: string; code: string }) =>
      (await unwrap(api.POST("/v1/auth/otp/verify", { body: { phone, purpose: objet, code } }))).otp_token,
  });
}

export function useConnexion() {
  const { ouvrir } = useSession();
  return useMutation({
    mutationFn: async ({ phone, password }: { phone: string; password: string }) => {
      const e164 = versE164(phone);
      if (!e164) throw new Error("numero_invalide");
      const r = await unwrap(api.POST("/v1/auth/login", { body: { ...IDENTITE_APPAREIL, phone: e164, password } }));
      await ouvrir(r);
      return r.user;
    },
  });
}

export function useInscription() {
  const { ouvrir } = useSession();
  return useMutation({
    mutationFn: async (v: { otpToken: string; full_name: string; password: string }) => {
      const r = await unwrap(api.POST("/v1/auth/register", { body: { ...IDENTITE_APPAREIL, otp_token: v.otpToken, full_name: v.full_name, password: v.password, terms_accepted: true } }));
      await ouvrir(r);
    },
  });
}

export function useReinitialiserMotDePasse() {
  return useMutation({
    mutationFn: async (v: { otpToken: string; new_password: string }) => {
      await unwrap(api.POST("/v1/auth/password/reset", { body: { otp_token: v.otpToken, new_password: v.new_password } }));
    },
  });
}
