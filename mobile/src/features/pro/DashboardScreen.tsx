import { Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { Home, HousePlus } from "lucide-react-native";
import { francs } from "@/lib/format";
import { t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Badge } from "@/ui/components/Card";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useTableauDeBord, useMesAnnonces } from "./queries";

type TonStatut = "succes" | "avertissement" | "neutre" | "danger";
const STATUT_TON: Record<string, TonStatut> = {
  published: "succes",
  processing: "neutre",
  draft: "neutre",
  hidden: "avertissement",
  rented: "information" as TonStatut,
  archived: "neutre",
};

/** Carte métrique 2×2 conforme à la maquette Dashboard gérant. */
function CarteMetrique({ valeur, label, couleur }: { valeur: number | string; label: string; couleur?: string }) {
  const { c } = useTheme();
  return (
    <View
      style={{
        flex: 1,
        backgroundColor: c.surface,
        borderRadius: rayon.card,
        padding: sp[4],
        gap: 4,
        minHeight: 88,
        shadowColor: colors.night,
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.04,
        shadowRadius: 8,
        elevation: 1,
      }}
    >
      <Text variante="hero" couleur={couleur ?? c.primary} style={{ fontSize: 32, lineHeight: 38 }}>
        {valeur}
      </Text>
      <Text variante="legende" muted>{label}</Text>
    </View>
  );
}

/**
 * Tableau de bord gérant (EF-DSH-01 à EF-DSH-05).
 * Conforme à la maquette « Mobile · Dashboard gérant@1x.png » :
 * - Salutation "Gérant vérifié / Bonjour [Prénom]" + avatar initiales
 * - Indicateurs : vues sur 30 jours et au total, contacts, chambres en ligne et louées (plan v3, D2)
 * - Alerte jaune si une annonce sans vidéo
 * - Section "Mes chambres" : liste avec vignette bleu nuit + titre + statut + loyer + badge statut
 * - Bouton "+ Publier" jaune solaire sur les annonces brouillons
 */
export function DashboardScreen() {
  const { c } = useTheme();
  const router = useRouter();
  const { etat } = useSession();
  const tableau = useTableauDeBord();
  const annonces = useMesAnnonces();

  const prenom = etat.statut === "connecte"
    ? etat.user.full_name.split(" ")[0] ?? etat.user.full_name
    : "";

  return (
    <Screen scroll>
      <Logotype taille={28} />
      {/* ── En-tête salutation + avatar ── */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: sp[4] }}>
        <View>
          <Text variante="legende" muted>Gérant vérifié</Text>
          <Text variante="titre">Bonjour {prenom}</Text>
        </View>
        {/* À droite : l'action utile, publier une chambre (plan v3, I1), plutôt que des initiales */}
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Publier une chambre"
          onPress={() => router.push("/pro/nouvelle-annonce/infos" as never)}
          style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: pressed ? c.accentHover : c.accent, paddingHorizontal: sp[4], paddingVertical: sp[2], borderRadius: 999 })}
        >
          <HousePlus size={18} color={c.onAccent} />
          <Text variante="corpsGras" couleur={c.onAccent}>Publier</Text>
        </Pressable>
      </View>

      {/* ── Grille métriques 2×2 ── */}
      <QueryState query={tableau}>
        {(data) => (
          <>
            <View style={{ flexDirection: "row", gap: sp[3], marginBottom: sp[3] }}>
              <CarteMetrique valeur={data.views_30d ?? 0} label="Vues sur 30 jours" />
              <CarteMetrique valeur={data.views_total ?? 0} label="Vues au total" />
            </View>
            <View style={{ flexDirection: "row", gap: sp[3], marginBottom: sp[3] }}>
              <CarteMetrique valeur={data.conversations_30d ?? 0} label="Contacts reçus" />
              <CarteMetrique valeur={data.listings_by_status?.published ?? 0} label="Chambres en ligne" />
            </View>
            <View style={{ flexDirection: "row", gap: sp[3], marginBottom: sp[4] }}>
              <CarteMetrique valeur={data.listings_by_status?.rented ?? 0} label="Chambres louées" couleur={c.succes} />
              <CarteMetrique valeur={data.listings_by_status?.draft ?? 0} label="Brouillons" />
            </View>

          </>
        )}
      </QueryState>

      {/* ── Mes chambres ── */}
      <Text variante="titreSection" style={{ marginBottom: sp[3] }}>Mes chambres</Text>

      <QueryState
        query={annonces}
        vide={{
          quand: (data) => data.length === 0,
          titre: "Aucune annonce",
          texte: "Publie ta première chambre pour être visible par les étudiants.",
          action: "Publier une chambre",
          onAction: () => router.push("/pro/nouvelle-annonce/infos" as never),
        }}
      >
        {(liste) => (
          <View style={{ gap: sp[3] }}>
            {liste.map((annonce) => (
              <Pressable
                key={annonce.id}
                accessibilityRole="button"
                onPress={() => router.push(`/pro/annonce/${annonce.id}` as never)}
                style={({ pressed }) => ({
                  flexDirection: "row",
                  alignItems: "center",
                  gap: sp[3],
                  backgroundColor: pressed ? c.divider : c.surface,
                  borderRadius: rayon.card,
                  padding: sp[3],
                  shadowColor: colors.night,
                  shadowOffset: { width: 0, height: 2 },
                  shadowOpacity: 0.04,
                  shadowRadius: 8,
                  elevation: 1,
                })}
              >
                {/* Vignette bleu nuit */}
                <View
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: 12,
                    backgroundColor: colors.blueSoft,
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Home size={26} color={colors.primary} />
                </View>

                {/* Infos */}
                <View style={{ flex: 1, gap: 2 }}>
                  <Text variante="corpsGras" numberOfLines={1}>{annonce.title}</Text>
                  <Text variante="legende" muted numberOfLines={1}>
                    {[annonce.room_type_label, annonce.district_name].filter(Boolean).join(" · ")}
                  </Text>
                  <Text variante="legende" couleur={c.primary} style={{ fontWeight: "700" }}>
                    {francs(annonce.rent_amount)}
                    {annonce.status === "draft" ? (
                      <Text variante="legende" couleur={c.avertissementText} style={{ fontWeight: "700" }}>{"  ·  Brouillon, invisible"}</Text>
                    ) : (
                      <Text variante="legende" muted>{`  ·  ${annonce.views_total} vue${annonce.views_total > 1 ? "s" : ""}`}</Text>
                    )}
                  </Text>
                </View>

                {/* Badge statut ou bouton "+ Publier" pour les brouillons */}
                {annonce.status === "draft" ? (
                  // Étiquette, pas un bouton : toute la carte est déjà cliquable (pas de bouton dans un bouton).
                  <View style={{ backgroundColor: c.accent, borderRadius: 999, paddingHorizontal: sp[3], paddingVertical: sp[2] }}>
                    <Text variante="corpsGras" couleur={c.onAccent}>Continuer</Text>
                  </View>
                ) : (
                  <Badge
                    titre={t.statutAnnonce[annonce.status] ?? annonce.status}
                    ton={(STATUT_TON[annonce.status] ?? "neutre") as any}
                  />
                )}
              </Pressable>
            ))}
          </View>
        )}
      </QueryState>

      {/* Bouton flottant nouvelle annonce */}
      <Button
        titre="+ Nouvelle chambre"
        variante="primaire"
        style={{ marginTop: sp[4] }}
        onPress={() => router.push("/pro/nouvelle-annonce/infos" as never)}
      />
    </Screen>
  );
}
