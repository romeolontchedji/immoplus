import { useState } from "react";
import { FlatList, Pressable, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { Bell, Home, Mail, MessageSquare } from "lucide-react-native";
import { dateCourte } from "@/lib/format";
import { useSession } from "@/state/session";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { Screen } from "@/ui/components/Screen";
import { EmptyState, ErrorState } from "@/ui/components/States";
import { SkeletonListe } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { useMarquerLue, useNotifications, useToutMarquerLu } from "./queries";
import { destination } from "./routage";

type FiltreNotif = "toutes" | "non_lues" | "alertes" | "messages";

/**
 * NotificationsScreen conforme à la maquette Mobile · Notifications@1x.png :
 * - Titre "Notifications" avec badge bleu "N non lues"
 * - Action "✓ Tout marquer comme lu"
 * - Filtres en chips horizontales : Toutes, Non lues, Alertes, Messages
 * - Cartes non lues sur fond bleu pastel #EFF4FF avec puce bleue et icône cobalt
 * - Cartes lues sur fond blanc avec icône grise et coche de lecture.
 */
export function NotificationsScreen() {
  const router = useRouter();
  const { role } = useSession();
  const requete = useNotifications();
  const lire = useMarquerLue();
  const toutLire = useToutMarquerLu();
  const [filtre, setFiltre] = useState<FiltreNotif>("toutes");

  const items = requete.data?.pages.flatMap((p) => p.items) ?? [];
  const nonLuesCount = items.filter((n) => !n.read_at).length;

  const itemsFiltres = items.filter((item) => {
    if (filtre === "non_lues") return !item.read_at;
    if (filtre === "alertes") return item.kind.includes("alert") || item.kind.includes("listing");
    if (filtre === "messages") return item.kind.includes("chat") || item.kind.includes("message");
    return true;
  });

  const getIcone = (kind: string, nonLue: boolean) => {
    const couleur = nonLue ? "#FFFFFF" : colors.textMuted;
    if (kind.includes("chat") || kind.includes("message")) {
      return <MessageSquare size={18} color={couleur} />;
    }
    if (kind.includes("listing")) {
      return <Home size={18} color={couleur} />;
    }
    return <Bell size={18} color={couleur} />;
  };

  return (
    <Screen flush>
      <AuthRequired>
        {requete.data === undefined ? (
          requete.isError ? (
            <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} />
          ) : (
            <View style={{ padding: sp[4], gap: sp[3], paddingTop: 40 }}>
              <SkeletonListe />
            </View>
          )
        ) : (
          <FlatList
            data={itemsFiltres}
            keyExtractor={(n) => n.id}
            contentContainerStyle={{ padding: sp[4], gap: sp[3], paddingBottom: 40 }}
            ListHeaderComponent={
              <View style={{ gap: sp[3], paddingBottom: sp[2] }}>
                {/* En-tête : Titre + Badge non lues */}
                <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
                  <Text
                    style={{
                      fontSize: 28,
                      fontWeight: "800",
                      color: colors.night,
                      letterSpacing: -0.5,
                    }}
                  >
                    Notifications
                  </Text>

                  {nonLuesCount > 0 ? (
                    <View
                      style={{
                        backgroundColor: colors.primary,
                        paddingHorizontal: 10,
                        paddingVertical: 4,
                        borderRadius: rayon.pilule,
                      }}
                    >
                      <Text style={{ color: "#FFFFFF", fontSize: 12, fontWeight: "700" }}>
                        {nonLuesCount} non lue{nonLuesCount > 1 ? "s" : ""}
                      </Text>
                    </View>
                  ) : null}
                </View>

                {/* Lien Tout marquer comme lu */}
                {nonLuesCount > 0 ? (
                  <Pressable
                    disabled={toutLire.isPending}
                    onPress={() => toutLire.mutate()}
                    style={{ alignSelf: "flex-start" }}
                  >
                    <Text style={{ fontSize: 14, fontWeight: "700", color: colors.primary }}>
                      ✓ Tout marquer comme lu
                    </Text>
                  </Pressable>
                ) : null}

                {/* Filtres par onglets / chips */}
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={{ gap: 8, marginTop: 4 }}
                >
                  {[
                    { id: "toutes", label: "Toutes" },
                    { id: "non_lues", label: `Non lues · ${nonLuesCount}` },
                    { id: "alertes", label: "Alertes" },
                    { id: "messages", label: "Messages" },
                  ].map((f) => {
                    const actif = filtre === f.id;
                    return (
                      <Pressable
                        key={f.id}
                        onPress={() => setFiltre(f.id as FiltreNotif)}
                        style={{
                          paddingHorizontal: 16,
                          paddingVertical: 9,
                          borderRadius: 999,
                          backgroundColor: actif ? colors.night : "#FFFFFF",
                          borderWidth: 1.5,
                          borderColor: actif ? colors.night : "rgba(15, 27, 61, 0.1)",
                        }}
                      >
                        <Text
                          style={{
                            fontSize: 13,
                            fontWeight: "700",
                            color: actif ? "#FFFFFF" : colors.night,
                          }}
                        >
                          {f.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </ScrollView>
              </View>
            }
            ListEmptyComponent={
              <EmptyState
                titre="Aucune notification"
                texte="Tu seras notifié dès qu'un message ou une chambre correspondante arrive."
              />
            }
            onEndReached={() => requete.hasNextPage && void requete.fetchNextPage()}
            renderItem={({ item }) => {
              const nonLue = !item.read_at;
              return (
                <Pressable
                  accessibilityRole="button"
                  onPress={() => {
                    if (nonLue) lire.mutate(item.id);
                    router.push(destination(item.kind, item.data as Record<string, unknown>, role));
                  }}
                  style={{
                    backgroundColor: nonLue ? "#EFF4FF" : "#FFFFFF",
                    borderRadius: 20,
                    padding: 16,
                    flexDirection: "row",
                    gap: 14,
                    alignItems: "flex-start",
                    borderWidth: 1,
                    borderColor: nonLue ? "rgba(27, 68, 214, 0.15)" : "rgba(15, 27, 61, 0.06)",
                    shadowColor: colors.night,
                    shadowOffset: { width: 0, height: 2 },
                    shadowOpacity: 0.04,
                    shadowRadius: 8,
                    elevation: 1,
                  }}
                >
                  {/* Conteneur d'icône */}
                  <View
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 14,
                      backgroundColor: nonLue ? colors.primary : "#F1F5F9",
                      justifyContent: "center",
                      alignItems: "center",
                      marginTop: 2,
                    }}
                  >
                    {getIcone(item.kind, nonLue)}
                  </View>

                  {/* Contenu textuel */}
                  <View style={{ flex: 1, gap: 3 }}>
                    <Text
                      style={{
                        fontSize: 15,
                        fontWeight: "700",
                        color: colors.night,
                      }}
                    >
                      {item.title}
                    </Text>

                    <Text
                      style={{
                        fontSize: 14,
                        color: colors.textMuted,
                        lineHeight: 20,
                      }}
                    >
                      {item.body}
                    </Text>

                    <Text
                      style={{
                        fontSize: 12,
                        fontWeight: nonLue ? "700" : "500",
                        color: nonLue ? colors.primary : colors.textMuted,
                        marginTop: 2,
                      }}
                    >
                      {dateCourte(item.created_at)} {nonLue ? "· Non lue" : "· Lue ✓"}
                    </Text>
                  </View>

                  {/* Puce bleue non lue */}
                  {nonLue ? (
                    <View
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 5,
                        backgroundColor: colors.primary,
                        marginTop: 6,
                      }}
                    />
                  ) : null}
                </Pressable>
              );
            }}
          />
        )}
      </AuthRequired>
    </Screen>
  );
}
