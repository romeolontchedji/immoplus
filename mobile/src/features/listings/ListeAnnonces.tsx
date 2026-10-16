import { FlatList, RefreshControl, View } from "react-native";
import { useRouter } from "expo-router";
import type { UseInfiniteQueryResult, InfiniteData } from "@tanstack/react-query";
import type { components } from "@/api/genere/api";
import { t } from "@/i18n/fr";
import { sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { ListingCard } from "@/ui/components/ListingCard";
import { EmptyState, ErrorState } from "@/ui/components/States";
import { SkeletonListe } from "@/ui/components/Skeleton";

type Page = components["schemas"]["FilOut"];

/** Liste paginée de cartes (fil, recherche) : squelettes, erreur avec « Réessayer », vide avec action, tirer pour actualiser, défilement infini. */
export function ListeAnnonces({ requete, vide, enTete }: {
  requete: UseInfiniteQueryResult<InfiniteData<Page>>;
  vide: { titre: string; texte?: string; action?: string; onAction?: () => void };
  enTete?: React.ReactElement;
}) {
  const router = useRouter();
  if (requete.data === undefined) return requete.isError ? <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} /> : <View style={{ padding: sp[4], gap: sp[4] }}><SkeletonListe /></View>;
  const cartes = requete.data.pages.flatMap((p) => p.items);
  return (
    <FlatList
      data={cartes}
      keyExtractor={(a) => a.id}
      ListHeaderComponent={enTete}
      renderItem={({ item }) => <ListingCard annonce={item} onPress={() => router.push({ pathname: "/annonces/[ident]", params: { ident: item.slug } })} />}
      contentContainerStyle={{ padding: sp[4], gap: sp[4] }}
      ListEmptyComponent={<EmptyState {...vide} />}
      ListFooterComponent={requete.hasNextPage ? <Button titre={t.commun.voirPlus} variante="secondaire" chargement={requete.isFetchingNextPage} onPress={() => void requete.fetchNextPage()} /> : null}
      onEndReachedThreshold={0.6}
      onEndReached={() => requete.hasNextPage && !requete.isFetchingNextPage && void requete.fetchNextPage()}
      refreshControl={<RefreshControl refreshing={requete.isRefetching && !requete.isFetchingNextPage} onRefresh={() => void requete.refetch()} />}
    />
  );
}
