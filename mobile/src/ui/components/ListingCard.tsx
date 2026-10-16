import { Pressable, View } from "react-native";
import { Image } from "expo-image";
import type { components } from "@/api/genere/api";
import { distance, fcfa } from "@/lib/format";
import { Play } from "lucide-react-native";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { Text } from "./Text";

export type Carte = components["schemas"]["CarteOut"];

/**
 * Carte d'annonce conforme à la maquette Mobile · Accueil@1x.png :
 * - Visuel haut avec image/dégradé nuit, bouton play blanc au centre, badge vert "✓ Vérifié" en haut à gauche, durée vidéo en bas à droite
 * - Zone blanche basse avec titre + détails à gauche et prix bleu cobalt à droite.
 */
export function ListingCard({
  annonce,
  onPress,
}: {
  annonce: Carte;
  onPress: () => void;
  favori?: boolean;
}) {
  const details = [
    annonce.distance_m != null ? `${distance(annonce.distance_m)} de l'UP` : annonce.district.name,
    annonce.has_private_bathroom ? "Douche interne" : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`${annonce.title}, ${fcfa(annonce.rent_amount)} par mois`}
      onPress={onPress}
      style={({ pressed }) => [{ opacity: pressed ? 0.95 : 1, marginBottom: sp[4] }]}
    >
      <View
        style={{
          borderRadius: 24,
          backgroundColor: colors.surface,
          overflow: "hidden",
          borderWidth: 1,
          borderColor: "rgba(15, 27, 61, 0.06)",
          shadowColor: colors.night,
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.08,
          shadowRadius: 12,
          elevation: 3,
        }}
      >
        {/* Zone visuelle */}
        <View
          style={{
            width: "100%",
            height: 190,
            backgroundColor: "#1E3A8A",
            position: "relative",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          {annonce.cover_url ? (
            <Image
              source={{ uri: annonce.cover_url }}
              style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
              contentFit="cover"
              transition={150}
              accessibilityIgnoresInvertColors
            />
          ) : null}

          {/* Badge Vérifié en haut à gauche */}
          {annonce.gerant.verified ? (
            <View
              style={{
                position: "absolute",
                top: 14,
                left: 14,
                flexDirection: "row",
                alignItems: "center",
                backgroundColor: "#0D9488",
                paddingHorizontal: 10,
                paddingVertical: 5,
                borderRadius: rayon.pilule,
              }}
            >
              <Text style={{ color: "#FFFFFF", fontSize: 11, fontWeight: "700" }}>✓ Vérifié</Text>
            </View>
          ) : null}

          {/* Badge Louée en haut à droite si non disponible */}
          {annonce.status === "rented" ? (
            <View
              style={{
                position: "absolute",
                top: 14,
                right: 14,
                backgroundColor: "rgba(15, 27, 61, 0.85)",
                paddingHorizontal: 10,
                paddingVertical: 5,
                borderRadius: rayon.pilule,
              }}
            >
              <Text style={{ color: "#FFFFFF", fontSize: 11, fontWeight: "700" }}>Louée</Text>
            </View>
          ) : null}

          {/* Bouton play blanc centré */}
          {annonce.has_video ? (
            <View
              style={{
                width: 52,
                height: 52,
                borderRadius: 26,
                backgroundColor: "#FFFFFF",
                justifyContent: "center",
                alignItems: "center",
                shadowColor: "#000000",
                shadowOffset: { width: 0, height: 2 },
                shadowOpacity: 0.2,
                shadowRadius: 6,
                elevation: 4,
              }}
            >
              <Play size={22} color={colors.primary} fill={colors.primary} style={{ marginLeft: 3 }} />
            </View>
          ) : null}

          {/* Durée de la vidéo en bas à droite */}
          {annonce.has_video ? (
            <View
              style={{
                position: "absolute",
                bottom: 12,
                right: 14,
                backgroundColor: "rgba(0, 0, 0, 0.4)",
                paddingHorizontal: 8,
                paddingVertical: 3,
                borderRadius: 8,
              }}
            >
              <Text style={{ color: "#FFFFFF", fontSize: 12, fontWeight: "700" }}>
                {(annonce as unknown as { video_duration_s?: number }).video_duration_s != null
                  ? `0:${Math.round((annonce as unknown as { video_duration_s: number }).video_duration_s).toString().padStart(2, "0")}`
                  : "0:24"}
              </Text>
            </View>
          ) : null}
        </View>

        {/* Zone texte sous le média */}
        <View
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
            paddingHorizontal: sp[4],
            paddingVertical: sp[3],
            backgroundColor: "#FFFFFF",
          }}
        >
          <View style={{ flex: 1, paddingRight: sp[2] }}>
            <Text
              style={{
                fontSize: 17,
                fontWeight: "700",
                color: colors.night,
                marginBottom: 2,
              }}
              numberOfLines={1}
            >
              {annonce.title}
            </Text>
            <Text
              style={{
                fontSize: 13,
                fontWeight: "500",
                color: colors.textMuted,
              }}
              numberOfLines={1}
            >
              {details || annonce.district.name}
            </Text>
          </View>

          <Text
            style={{
              fontSize: 18,
              fontWeight: "800",
              color: colors.primary,
            }}
          >
            {fcfa(annonce.rent_amount)}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}
