import { View } from "react-native";
import { Pressable } from "react-native";
import { useRouter } from "expo-router";
import { CIBLE_MIN, colors, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Text } from "@/ui/components/Text";

type Props = {
  etape: number;     // 1-based
  total: number;
  titre?: string;
};

/**
 * En-tête partagé du tunnel de publication.
 * Conforme à la maquette « Mobile · Publier@1x.png » :
 * - Flèche ← retour · Titre centré « Publier une chambre » · « Étape N/M » à droite
 * - Barre de progression segmentée (segments bleu cobalt / gris)
 */
export function EntetePublication({ etape, total, titre = "Publier une chambre" }: Props) {
  const { c } = useTheme();
  const router = useRouter();

  return (
    <View style={{ gap: sp[2] }}>
      {/* Ligne de navigation */}
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Retour"
          onPress={() => router.back()}
          style={{ minHeight: CIBLE_MIN, justifyContent: "center", paddingRight: sp[3], width: 48 }}
        >
          <Text style={{ fontSize: 20, color: c.text }}>←</Text>
        </Pressable>
        <Text variante="corps" style={{ flex: 1, textAlign: "center", fontWeight: "600" }}>{titre}</Text>
        <Text variante="legende" muted style={{ width: 56, textAlign: "right" }}>
          Étape {etape}/{total}
        </Text>
      </View>

      {/* Barre de progression segmentée (conforme maquette : 4 segments) */}
      <View style={{ flexDirection: "row", gap: 4, height: 4 }}>
        {Array.from({ length: total }, (_, i) => (
          <View
            key={i}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              backgroundColor: i < etape ? colors.blue : c.border,
            }}
          />
        ))}
      </View>
    </View>
  );
}
