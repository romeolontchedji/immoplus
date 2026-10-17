import { Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { Home } from "lucide-react-native";
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
        shadowColor: "#0F1B3D",
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
 * - Grille 2×2 métriques : Vues ce mois / Contacts reçus / Chambres actives / Chambre louée
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
  const initiales = etat.statut === "connecte"
    ? etat.user.full_name.split(" ").slice(0, 2).map((m) => m[0]?.toUpperCase() ?? "").join("")
    : "";

  return (
    <Screen scroll>
      <Logotype taille={34} />
      {/* ── En-tête salutation + avatar ── */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: sp[4] }}>
        <View>
          <Text variante="legende" muted>Gérant vérifié</Text>
          <Text variante="titre">Bonjour {prenom}</Text>
        </View>
        <View
          style={{
            width: 44,
            height: 44,
            borderRadius: 22,
            backgroundColor: c.primarySoft,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Text variante="legende" couleur={c.primary} style={{ fontWeight: "800" }}>{initiales}</Text>
        </View>
      </View>

      {/* ── Grille métriques 2×2 ── */}
      <QueryState query={tableau}>
        {(data) => (
          <>
            <View style={{ flexDirection: "row", gap: sp[3], marginBottom: sp[3] }}>
              <CarteMetrique valeur={data.views_30d ?? 0} label="Vues ce mois" />
              <CarteMetrique valeur={data.conversations_30d ?? 0} label="Contacts reçus" />
            </View>
            <View style={{ flexDirection: "row", gap: sp[3], marginBottom: sp[4] }}>
              <CarteMetrique valeur={data.listings_by_status?.published ?? 0} label="Chambres en ligne" />
              <CarteMetrique valeur={data.listings_by_status?.rented ?? 0} label="Chambres louées" couleur={c.succes} />
            </View>

            {/* Bandeau jaune : annonces dont la disponibilité est à reconfirmer (sinon elles sont masquées) */}
            {data.to_confirm > 0 ? (
              <View
                style={{
                  backgroundColor: c.avertissementBg,
                  borderRadius: rayon.card,
                  padding: sp[4],
                  marginBottom: sp[4],
                  gap: 4,
                }}
              >
                <Text variante="corpsGras" couleur={c.avertissementText}>
                  {data.to_confirm === 1 ? "Une annonce" : `${data.to_confirm} annonces`} à confirmer.
                </Text>
                <Text variante="legende" couleur={c.avertissementText}>
                  Confirme qu’elles sont toujours libres pour qu’elles restent visibles.
                </Text>
              </View>
            ) : null}
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
                  shadowColor: "#0F1B3D",
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
                    {[t.typeChambre[annonce.room_type] ?? annonce.room_type, annonce.district_name].filter(Boolean).join(" · ")}
                  </Text>
                  <Text variante="legende" couleur={c.primary} style={{ fontWeight: "700" }}>
                    {francs(annonce.rent_amount)}
                  </Text>
                </View>

                {/* Badge statut ou bouton "+ Publier" pour les brouillons */}
                {annonce.status === "draft" ? (
                  <Button
                    titre="+ Publier"
                    variante="accent"
                    taille="compacte"
                    onPress={() => router.push(`/pro/annonce/${annonce.id}` as never)}
                  />
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
