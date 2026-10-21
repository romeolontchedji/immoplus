import { useState } from "react";
import { FlatList, RefreshControl, View } from "react-native";
import { MapPin } from "lucide-react-native";
import { useRouter } from "expo-router";
import type { UseInfiniteQueryResult, InfiniteData } from "@tanstack/react-query";
import type { components } from "@/api/genere/api";
import { t } from "@/i18n/fr";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { Text } from "@/ui/components/Text";
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
  // Indicateur réservé au geste « tirer pour rafraîchir » : la recherche au fil de la frappe ne l'affiche jamais.
  const [tire, setTire] = useState(false);
  if (requete.data === undefined) return requete.isError ? <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} /> : <View style={{ padding: sp[4], gap: sp[4] }}><SkeletonListe /></View>;
  const cartes = requete.data.pages.flatMap((p) => p.items);
  const voisins = requete.data.pages[0]?.voisins;
  const ouvrir = (slug: string) => router.push({ pathname: "/annonces/[ident]", params: { ident: slug } });
  // Quartiers voisins (plan v3, A4) : proposés à part, jamais mélangés aux résultats demandés.
  const blocVoisins = voisins?.items.length ? (
    <View style={{ gap: sp[3], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.warningBg, borderWidth: 1, borderColor: colors.sun }}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: sp[3] }}>
        <MapPin size={20} color={colors.night} />
        <View style={{ flex: 1, gap: 2 }}>
          <Text variante="corpsGras">Aussi dans les quartiers voisins</Text>
          <Text variante="legende" muted>Mêmes critères, à quelques minutes : {voisins.districts.map((d) => d.name).join(", ")}</Text>
        </View>
      </View>
      {voisins.items.map((item) => <ListingCard key={item.id} annonce={item} onPress={() => ouvrir(item.slug)} />)}
    </View>
  ) : null;
  return (
    <FlatList
      data={cartes}
      keyExtractor={(a) => a.id}
      ListHeaderComponent={enTete}
      renderItem={({ item }) => <ListingCard annonce={item} onPress={() => ouvrir(item.slug)} />}
      contentContainerStyle={{ padding: sp[4], gap: sp[4] }}
      ListEmptyComponent={voisins?.items.length ? <EmptyState titre="Aucune chambre dans ce quartier" texte="Regarde juste en dessous : des chambres avec les mêmes critères tout près." /> : <EmptyState {...vide} />}
      ListFooterComponent={
        <View style={{ gap: sp[4] }}>
          {requete.hasNextPage ? <Button titre={t.commun.voirPlus} variante="secondaire" chargement={requete.isFetchingNextPage} onPress={() => void requete.fetchNextPage()} /> : null}
          {blocVoisins}
        </View>
      }
      onEndReachedThreshold={0.6}
      onEndReached={() => requete.hasNextPage && !requete.isFetchingNextPage && void requete.fetchNextPage()}
      refreshControl={<RefreshControl refreshing={tire} onRefresh={() => { setTire(true); void requete.refetch().finally(() => setTire(false)); }} />}
    />
  );
}
