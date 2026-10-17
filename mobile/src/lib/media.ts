import { API_URL } from "@/config/env";

/** Les médias sont servis sous `/media/…` (chemin relatif côté serveur) : on les rattache à l'hôte de l'API. */
export function urlMedia(chemin: string | null | undefined): string | undefined {
  if (!chemin) return undefined;
  return /^https?:\/\//.test(chemin) ? chemin : `${API_URL}${chemin.startsWith("/") ? "" : "/"}${chemin}`;
}
