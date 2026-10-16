import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";
import type { components } from "@/api/genere/api";

export type Alerte = components["schemas"]["AlerteOut"];
export type AlerteEntree = components["schemas"]["AlerteIn"];

export const useAlertes = (actif = true) => useQuery({ queryKey: qk.alertes, queryFn: () => unwrap(api.GET("/v1/me/alerts")), enabled: actif });

export function useCreerAlerte() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (corps: AlerteEntree) => unwrap(api.POST("/v1/me/alerts", { body: corps })), onSuccess: () => void qc.invalidateQueries({ queryKey: qk.alertes }) });
}

export function useModifierAlerte(id: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (corps: AlerteEntree) => unwrap(api.PATCH("/v1/me/alerts/{alerte_id}", { params: { path: { alerte_id: id } }, body: corps })), onSuccess: () => void qc.invalidateQueries({ queryKey: qk.alertes }) });
}

export function useSupprimerAlerte() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => unwrap(api.DELETE("/v1/me/alerts/{alerte_id}", { params: { path: { alerte_id: id } } })), onSuccess: () => void qc.invalidateQueries({ queryKey: qk.alertes }) });
}
