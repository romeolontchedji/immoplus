import { FlatList, Pressable, RefreshControl, View } from "react-native";
import { useRouter } from "expo-router";
import { heure } from "@/lib/format";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { Badge, Card } from "@/ui/components/Card";
import { Screen } from "@/ui/components/Screen";
import { EmptyState, ErrorState } from "@/ui/components/States";
import { SkeletonListe } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { useConversations } from "./queries";

/** Onglet « Messages » (locataire et gérant) : conversations triées par activité, pastille de non-lus, aperçu du dernier message. */
export function ConversationsScreen({ annonceId }: { annonceId?: string }) {
  const router = useRouter();
  const { c } = useTheme();
  const requete = useConversations(annonceId);
  return (
    <Screen flush>
      <AuthRequired>
        {requete.data === undefined ? (
          requete.isError ? <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} /> : <View style={{ padding: sp[4], gap: sp[3] }}><SkeletonListe /></View>
        ) : (
          <FlatList
            data={requete.data.pages.flatMap((p) => p.items)}
            keyExtractor={(x) => x.id}
            contentContainerStyle={{ padding: sp[4], gap: sp[3] }}
            ListEmptyComponent={<EmptyState titre="Aucune conversation" texte="Écris à un gérant depuis la fiche d'une annonce." />}
            refreshControl={<RefreshControl refreshing={requete.isRefetching} onRefresh={() => void requete.refetch()} />}
            onEndReached={() => requete.hasNextPage && void requete.fetchNextPage()}
            renderItem={({ item }) => (
              <Pressable accessibilityRole="button" onPress={() => router.push({ pathname: "/conversation/[id]", params: { id: item.id } })}>
                <Card style={{ padding: sp[3], gap: sp[1], borderColor: item.unread_count ? c.primary : c.border }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", gap: sp[2] }}>
                    <Text variante="sousTitre" numberOfLines={1} style={{ flex: 1 }}>{item.other.name ?? "Utilisateur"}</Text>
                    {item.last_message_at ? <Text variante="legende" muted>{heure(item.last_message_at)}</Text> : null}
                  </View>
                  <Text variante="legende" muted numberOfLines={1}>{item.listing.title}</Text>
                  <Text numberOfLines={1}>{item.last_message_preview}</Text>
                  <View style={{ flexDirection: "row", gap: sp[2] }}>
                    {item.unread_count ? <Badge titre={`${item.unread_count} non lu${item.unread_count > 1 ? "s" : ""}`} ton="marque" /> : null}
                    {item.status !== "open" ? <Badge titre={item.status === "blocked" ? "Bloquée" : "Lecture seule"} ton="avertissement" /> : null}
                    {item.muted ? <Badge titre="En sourdine" /> : null}
                  </View>
                </Card>
              </Pressable>
            )}
          />
        )}
      </AuthRequired>
    </Screen>
  );
}
