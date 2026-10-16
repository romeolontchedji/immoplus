import { Pressable } from "react-native";
import { CIBLE_MIN, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Text } from "./Text";

export function Chip({ titre, actif, onPress }: { titre: string; actif: boolean; onPress: () => void }) {
  const { c } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: actif }}
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: CIBLE_MIN - 8,
        paddingHorizontal: sp[4],
        borderRadius: rayon.pilule,
        justifyContent: "center",
        borderWidth: 1.5,
        // Actif : fond bleu cobalt + texte blanc (conforme maquettes Accueil, Filtres, Alertes)
        borderColor: actif ? c.primary : c.borderStrong,
        backgroundColor: actif ? c.primary : (pressed ? c.divider : c.surface),
      })}
    >
      <Text variante="legende" couleur={actif ? "#FFFFFF" : c.text} style={{ fontWeight: "600" }}>{titre}</Text>
    </Pressable>
  );
}
