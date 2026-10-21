import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { qk } from "@/api/keys";

export function useNotifications() {
  return useInfiniteQuery({
    queryKey: qk.notifications,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => unwrap(api.GET("/v1/notifications", { params: { query: { cursor: pageParam } } })),
    getNextPageParam: (p) => p.next_cursor ?? undefined,
  });
}

/** Compteur de la pastille (borné à 100 côté serveur : « 99+ »). Mis à jour en direct par `notification.new`. */
export function useNonLues(actif = true) {
  return useQuery({ queryKey: qk.nonLues, queryFn: () => unwrap(api.GET("/v1/notifications/unread-count")), enabled: actif, staleTime: 60_000 });
}

export function useMarquerLue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.POST("/v1/notifications/{notification_id}/read", { params: { path: { notification_id: id } } })),
    onSuccess: () => void Promise.all([qc.invalidateQueries({ queryKey: qk.notifications }), qc.invalidateQueries({ queryKey: qk.nonLues })]),
  });
}

export function useToutMarquerLu() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.POST("/v1/notifications/read-all")),
    onSuccess: () => void Promise.all([qc.invalidateQueries({ queryKey: qk.notifications }), qc.invalidateQueries({ queryKey: qk.nonLues })]),
  });
}
