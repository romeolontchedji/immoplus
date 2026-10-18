import { useMemo, useState } from "react";
import { FlatList, Pressable, RefreshControl, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { Ban, BellOff, Search, X } from "lucide-react-native";
import { heure, jourRelatif } from "@/lib/format";
import { useSession } from "@/state/session";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { Chip } from "@/ui/components/Chip";
import { EnTetePage } from "@/ui/components/EnTetePage";
import { Avatar } from "@/ui/components/Groupe";
import { Screen } from "@/ui/components/Screen";
import { EmptyState, ErrorState } from "@/ui/components/States";
import { SkeletonListe } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { BalayageConversation } from "./BalayageConversation";
import { MenuConversation } from "./MenuConversation";
import { useConversations } from "./queries";

type Conversation = NonNullable<ReturnType<typeof useConversations>["data"]>["pages"][number]["items"][number];

/** Heure du dernier message (aujourd'hui), « Hier », ou la date courte. */
function quand(iso: string): string {
  const jour = jourRelatif(iso);
  return jour === "Aujourd'hui" ? heure(iso) : jour === "Hier" ? "Hier" : jour.replace(/ \d{4}$/, "");
}

function Ligne({ item, onPress, onLongPress }: { item: Conversation; onPress: () => void; onLongPress: () => void }) {
  const nom = item.other.name ?? "Utilisateur";
  const nonLu = item.unread_count > 0;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${nom}, ${item.listing.title ?? ""}${nonLu ? `, ${item.unread_count} non lus` : ""}`}
      accessibilityHint="Balayer vers la gauche : lu, sourdine. Appui long : plus de choix"
      onPress={onPress}
      onLongPress={onLongPress}
      style={({ pressed }) => ({ flexDirection: "row", gap: sp[3], paddingHorizontal: sp[4], paddingVertical: sp[3], backgroundColor: pressed ? colors.divider : colors.surface, opacity: item.muted ? 0.75 : 1 })}
    >
      <Avatar nom={nom} id={item.id} taille={52} />
      <View style={{ flex: 1, gap: 2, justifyContent: "center" }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
          <Text variante="corpsGras" numberOfLines={1} style={{ flex: 1 }}>{nom}</Text>
          {item.last_message_at ? (
            <Text variante="legende" couleur={nonLu ? colors.primary : colors.textMuted} style={{ fontWeight: nonLu ? "800" : "400" }}>{quand(item.last_message_at)}</Text>
          ) : null}
        </View>
        {item.listing.title ? <Text variante="legende" couleur={colors.primary} numberOfLines={1}>{item.listing.title}</Text> : null}
        <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
          {item.status === "blocked" ? <Ban size={14} color={colors.textMuted} /> : null}
          <Text numberOfLines={1} style={{ flex: 1, fontSize: 14, color: nonLu ? colors.night : colors.textMuted, fontWeight: nonLu ? "600" : "400" }}>
            {item.status === "blocked" ? "Conversation bloquée" : item.status === "read_only" ? "Lecture seule" : item.last_message_preview || "Nouvelle conversation"}
          </Text>
          {item.muted ? <BellOff size={14} color={colors.textMuted} /> : null}
          {nonLu ? (
            <View style={{ minWidth: 22, height: 22, paddingHorizontal: 6, borderRadius: 11, backgroundColor: item.muted ? colors.sable300 : colors.primary, alignItems: "center", justifyContent: "center" }}>
              <Text style={{ color: colors.white, fontSize: 12, fontWeight: "800" }}>{item.unread_count > 99 ? "99+" : item.unread_count}</Text>
            </View>
          ) : null}
        </View>
      </View>
    </Pressable>
  );
}

/**
 * Onglet « Messages » (locataire et gérant), façon WhatsApp (plan v2, MM2, MM8) : avatar, nom, chambre liée, extrait,
 * heure, pastille de non-lus, sourdine grisée ; recherche, filtre « Non lues » (« À répondre » pour le gérant),
 * appui long pour le menu de la conversation.
 */
export function ConversationsScreen({ annonceId }: { annonceId?: string }) {
  const router = useRouter();
  const { role } = useSession();
  const requete = useConversations(annonceId);
  const [recherche, setRecherche] = useState("");
  const [nonLues, setNonLues] = useState(false);
  const [menu, setMenu] = useState<Conversation | null>(null);

  const toutes = useMemo(() => requete.data?.pages.flatMap((p) => p.items) ?? [], [requete.data]);
  const visibles = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return toutes.filter((c) => (!nonLues || c.unread_count > 0) && (!q || `${c.other.name ?? ""} ${c.listing.title ?? ""} ${c.last_message_preview}`.toLowerCase().includes(q)));
  }, [toutes, recherche, nonLues]);
  const totalNonLues = toutes.filter((c) => c.unread_count > 0).length;

  return (
    <Screen flush>
      <AuthRequired>
        <View style={{ paddingHorizontal: sp[4], paddingTop: sp[4], gap: sp[3], backgroundColor: colors.surface }}>
          <EnTetePage titre="Messages" />
          <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2], backgroundColor: colors.bg, borderRadius: rayon.pilule, paddingHorizontal: sp[4], height: 44 }}>
            <Search size={18} color={colors.textMuted} />
            <TextInput
              value={recherche}
              onChangeText={setRecherche}
              placeholder="Rechercher un nom, une chambre…"
              placeholderTextColor={colors.textMuted}
              accessibilityLabel="Rechercher dans les conversations"
              style={{ flex: 1, fontSize: 15, color: colors.night, paddingVertical: 0 }}
            />
            {recherche ? (
              <Pressable accessibilityLabel="Effacer la recherche" onPress={() => setRecherche("")} hitSlop={8}>
                <X size={18} color={colors.textMuted} />
              </Pressable>
            ) : null}
          </View>
          <View style={{ flexDirection: "row", gap: sp[2], paddingBottom: sp[3] }}>
            <Chip titre="Toutes" actif={!nonLues} onPress={() => setNonLues(false)} />
            <Chip titre={`${role === "gerant" ? "À répondre" : "Non lues"}${totalNonLues ? ` · ${totalNonLues}` : ""}`} actif={nonLues} onPress={() => setNonLues(true)} />
          </View>
        </View>
        {requete.data === undefined ? (
          requete.isError ? <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} /> : <View style={{ padding: sp[4], gap: sp[3] }}><SkeletonListe /></View>
        ) : (
          <FlatList
            data={visibles}
            keyExtractor={(x) => x.id}
            ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: colors.divider, marginLeft: 80 }} />}
            ListEmptyComponent={
              toutes.length === 0 ? (
                <EmptyState titre="Aucune conversation" texte={role === "gerant" ? "Les messages des étudiants intéressés par tes chambres arrivent ici." : "Écris à un gérant depuis la fiche d'une chambre."} />
              ) : (
                <Text muted style={{ textAlign: "center", padding: sp[8] }}>{nonLues ? "Tout est lu." : "Aucun résultat."}</Text>
              )
            }
            refreshControl={<RefreshControl refreshing={requete.isRefetching} onRefresh={() => void requete.refetch()} />}
            onEndReached={() => requete.hasNextPage && void requete.fetchNextPage()}
            renderItem={({ item }) => (
              <BalayageConversation conversation={item}>
                <Ligne item={item} onPress={() => router.push({ pathname: "/conversation/[id]", params: { id: item.id } })} onLongPress={() => setMenu(item)} />
              </BalayageConversation>
            )}
          />
        )}
        {menu ? <MenuConversation conversation={menu} autreNom={menu.other.name ?? "Utilisateur"} ouvert onFermer={() => setMenu(null)} /> : null}
      </AuthRequired>
    </Screen>
  );
}
