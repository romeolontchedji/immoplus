import type { ReactNode } from "react";
import { View } from "react-native";
import type { UseQueryResult } from "@tanstack/react-query";
import { isApiError, isNetworkError } from "@/api/errors";
import { useOnline } from "@/hooks/useOnline";
import { messageErreur, t } from "@/i18n/fr";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "./Button";
import { SkeletonListe } from "./Skeleton";
import { Text } from "./Text";

/** Bandeau « hors connexion » en haut de chaque écran (CDC §12.1). */
export function OfflineBanner() {
  const { c } = useTheme();
  if (useOnline()) return null;
  return (
    <View accessibilityRole="alert" style={{ backgroundColor: c.avertissementBg, padding: sp[2] }}>
      <Text variante="legende" couleur={c.avertissementText}>{t.commun.horsLigne}</Text>
    </View>
  );
}

export function EmptyState({ titre, texte, action, onAction }: { titre: string; texte?: string; action?: string; onAction?: () => void }) {
  return (
    <View style={{ alignItems: "center", gap: sp[3], padding: sp[6] }}>
      <Text variante="sousTitre" style={{ textAlign: "center" }}>{titre}</Text>
      {texte ? <Text muted style={{ textAlign: "center" }}>{texte}</Text> : null}
      {action && onAction ? <Button titre={action} onPress={onAction} /> : null}
    </View>
  );
}

export function ErrorState({ erreur, onRetry }: { erreur: unknown; onRetry?: () => void }) {
  const texte = isNetworkError(erreur) ? t.erreurs.network : isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.commun.erreurGenerique;
  return (
    <View accessibilityRole="alert" style={{ alignItems: "center", gap: sp[3], padding: sp[6] }}>
      <Text style={{ textAlign: "center" }}>{texte}</Text>
      {onRetry ? <Button titre={t.commun.reessayer} variante="secondaire" onPress={onRetry} /> : null}
    </View>
  );
}

/**
 * Les quatre états d'un écran alimenté par une requête : chargement (squelettes), erreur (« Réessayer »), vide (avec une
 * action) et contenu. Quand des données en cache existent, elles restent affichées même si l'actualisation échoue.
 */
export function QueryState<T>({ query, vide, children, squelette }: {
  query: UseQueryResult<T>;
  vide?: { quand: (donnees: T) => boolean; titre: string; texte?: string; action?: string; onAction?: () => void };
  children: (donnees: T) => ReactNode;
  squelette?: ReactNode;
}) {
  if (query.data === undefined) {
    if (query.isError) return <ErrorState erreur={query.error} onRetry={() => void query.refetch()} />;
    return <>{squelette ?? <SkeletonListe />}</>;
  }
  if (vide?.quand(query.data)) return <EmptyState titre={vide.titre} texte={vide.texte} action={vide.action} onAction={vide.onAction} />;
  return <>{children(query.data)}</>;
}
