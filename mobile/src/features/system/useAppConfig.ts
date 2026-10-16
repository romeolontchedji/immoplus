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
