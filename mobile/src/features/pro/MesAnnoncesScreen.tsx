import { useState } from "react";
import { FlatList, Pressable, RefreshControl, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { Eye, FilePen, Plus } from "lucide-react-native";
import { francs } from "@/lib/format";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Badge } from "@/ui/components/Card";
import { EnTetePage } from "@/ui/components/EnTetePage";
import { Chip } from "@/ui/components/Chip";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { type AnnoncePro, useMesAnnonces } from "./queries";
import { ONGLETS, STATUTS } from "./statuts";

/** Une annonce du gérant ; un brouillon est dessiné à part (pointillés, fond jaune) pour ne jamais être confondu (C5). */
function CarteAnnonce({ annonce, onPress }: { annonce: AnnoncePro; onPress: () => void }) {
  const statut = STATUTS[annonce.status] ?? { libelle: annonce.status, ton: "neutre" as const };
  const brouillon = annonce.status === "draft";
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${annonce.title}, ${statut.libelle}`}
      onPress={onPress}
      style={({ pressed }) => ({
        backgroundColor: brouillon ? colors.warningBg : pressed ? colors.bg : colors.surface,
        borderRadius: rayon.card, borderWidth: brouillon ? 2 : 1, borderStyle: brouillon ? "dashed" : "solid",
        borderColor: brouillon ? colors.sun : colors.divider, padding: sp[4], gap: sp[2], ...(brouillon ? {} : ombre.card),
      })}
    >
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: sp[3] }}>
        <Text variante="corpsGras" style={{ flex: 1 }} numberOfLines={2}>{annonce.title}</Text>
        {brouillon ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: colors.surface, borderRadius: rayon.pilule, paddingHorizontal: sp[2], paddingVertical: 3 }}>
            <FilePen size={13} color={colors.warning} />
            <Text style={{ fontSize: 12, fontWeight: "800", color: colors.warning }}>Brouillon</Text>
          </View>
        ) : (
          <Badge titre={statut.libelle} ton={statut.ton} />
        )}
      </View>
      <Text variante="legende" muted>{[annonce.room_type_label, annonce.district_name].filter(Boolean).join(" · ")}</Text>
      {brouillon ? <Text variante="legende" couleur={colors.warning} style={{ fontWeight: "700" }}>Invisible pour les locataires tant qu’elle n’est pas publiée.</Text> : null}
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <Text variante="corpsGras" couleur={colors.primary}>{`${francs(annonce.rent_amount)} / mois${annonce.rent_negotiable ? " · à débattre" : ""}`}</Text>
        {!brouillon ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
            <Eye size={14} color={colors.textMuted} />
            <Text variante="legende" muted>{`${annonce.views_total} vue${annonce.views_total > 1 ? "s" : ""}`}</Text>
          </View>
        ) : null}
      </View>
    </Pressable>
  );
}

/** Mes annonces (EF-ANN-01, EF-ANN-12 ; plan v2, MM4) : filtres par statut avec compteurs, accès à chaque annonce. */
export function MesAnnoncesScreen() {
  const router = useRouter();
  const requete = useMesAnnonces();
  const [onglet, setOnglet] = useState<(typeof ONGLETS)[number]["cle"]>("tout");

  return (
    <Screen flush>
      <View style={{ paddingHorizontal: sp[4], paddingTop: sp[4], gap: sp[3] }}>
        <EnTetePage
          titre="Mes chambres"
          droite={
            <Pressable
                accessibilityRole="button"
                accessibilityLabel="Publier une nouvelle chambre"
                onPress={() => router.push("/pro/nouvelle-annonce/infos" as never)}
                style={{ flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.sun, paddingHorizontal: sp[4], paddingVertical: sp[2], borderRadius: rayon.pilule }}
              >
                <Plus size={18} color={colors.night} />
                <Text variante="corpsGras">Publier</Text>
              </Pressable>
          }
        />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: sp[2] }}>
          {ONGLETS.map((o) => {
            const n = (requete.data ?? []).filter((a) => !o.statuts || (o.statuts as readonly string[]).includes(a.status)).length;
            return <Chip key={o.cle} titre={`${o.libelle} · ${n}`} actif={onglet === o.cle} onPress={() => setOnglet(o.cle)} />;
          })}
        </ScrollView>
      </View>
      <QueryState
        query={requete}
        vide={{ quand: (l) => l.length === 0, titre: "Aucune chambre publiée", texte: "Publie ta première chambre : une vidéo, quelques photos, et les étudiants te contactent.", action: "Publier une chambre", onAction: () => router.push("/pro/nouvelle-annonce/infos" as never) }}
      >
        {(liste) => {
          const filtre = ONGLETS.find((o) => o.cle === onglet)?.statuts;
          const visibles = liste.filter((a) => !filtre || (filtre as readonly string[]).includes(a.status));
          return (
            <FlatList
              data={visibles}
              keyExtractor={(a) => a.id}
              contentContainerStyle={{ padding: sp[4], gap: sp[3] }}
              refreshControl={<RefreshControl refreshing={requete.isRefetching} onRefresh={() => void requete.refetch()} />}
              ListEmptyComponent={<Text muted style={{ textAlign: "center", paddingTop: sp[8] }}>Aucune chambre dans cette catégorie.</Text>}
              renderItem={({ item }) => <CarteAnnonce annonce={item} onPress={() => router.push(`/pro/annonce/${item.id}` as never)} />}
            />
          );
        }}
      </QueryState>
    </Screen>
  );
}
