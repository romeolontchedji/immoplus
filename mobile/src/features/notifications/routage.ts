import type { Href } from "expo-router";

/**
 * Où mène une notification (appui sur le push ou sur une ligne du centre). Pure et testée : c'est ici, et seulement ici,
 * que se décide la navigation à partir de `kind` et `data` (voir docs/mobile/notifications-push.md).
 */
export function destination(kind: string | undefined, data: Record<string, unknown> | undefined, role: "client" | "gerant" | null): Href {
  const texte = (cle: string): string | undefined => (typeof data?.[cle] === "string" ? (data[cle] as string) : undefined);
  const conversation = texte("conversation_id");
  const annonce = texte("listing_id");
  const slug = texte("slug");
  switch (kind) {
    case "message.received":
    case "message.unanswered_reminder":
      return conversation ? { pathname: "/conversation/[id]", params: { id: conversation } } : "/notifications";
    case "alert.match":
    case "favorite.unavailable":
      return slug ? { pathname: "/annonces/[ident]", params: { ident: slug } } : "/notifications";
    case "alert.digest":
      return "/alertes"; // récapitulatif « N nouvelles chambres » : la liste des alertes et leurs résultats
    case "listing.published":
    case "listing.hidden":
    case "listing.reminder":
    case "listing.reported_rented":
    case "listing.rented_video_scheduled":
    case "listing.media_failed":
      return role === "gerant" && annonce ? { pathname: "/pro/annonce/[id]", params: { id: annonce } } : "/notifications";
    default:
      return "/notifications"; // sanction, inconnu : le centre explique
  }
}
