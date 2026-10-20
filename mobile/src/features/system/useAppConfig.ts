import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import type { components } from "@/api/genere/api";

export type AppConfig = components["schemas"]["AppConfigOut"];

/** Configuration distante : version minimale, maintenance, avis, drapeaux, limites. Relue toutes les 5 minutes et au retour au premier plan. */
export function useAppConfig() {
  return useQuery({
    queryKey: qk.appConfig,
    queryFn: () => unwrap(api.GET("/v1/app-config")),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: true,
  });
}

/** Repli si la configuration n'est pas encore chargée (hors ligne au premier lancement). */
const CONTACT_PAR_DEFAUT = { phone: "+2290156201400", whatsapp_url: "https://wa.me/2290156201400" };

/** Contact de l'équipe Immo+ (même source que le site : paramètre `TEAM_PHONE`). */
export function useContactEquipe() {
  const contact = useAppConfig().data?.contact ?? CONTACT_PAR_DEFAUT;
  const local = contact.phone.replace(/^\+229/, "");
  return { ...contact, telUrl: `tel:${contact.phone}`, affiche: `+229 ${local.replace(/(\d{2})(?=\d)/g, "$1 ")}` };
}
