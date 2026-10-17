import type { ReactNode } from "react";
import { Pressable } from "react-native";
import { X } from "lucide-react-native";
import { CIBLE_MIN, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Text } from "./Text";

type Props = {
  titre: string;
  actif: boolean;
  onPress: () => void;
  /** Icône Lucide placée avant le texte (reçoit la couleur courante). */
  icone?: (couleur: string) => ReactNode;
  /** Filtre actif retirable (DESIGN.md §Chips) : texte + icône `x`. */
  retirable?: boolean;
};

/** Pastille de filtre : inactive = blanc + bordure, active = cobalt + texte blanc. */
export function Chip({ titre, actif, onPress, icone, retirable }: Props) {
  const { c } = useTheme();
  const couleur = actif ? "#FFFFFF" : c.text;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: actif }}
      accessibilityLabel={retirable ? `Retirer le filtre ${titre}` : titre}
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: CIBLE_MIN - 8,
        paddingHorizontal: sp[4],
        borderRadius: rayon.pilule,
        flexDirection: "row",
        alignItems: "center",
        gap: 6,
        borderWidth: 1.5,
        borderColor: actif ? c.primary : c.border,
        backgroundColor: actif ? (pressed ? c.primaryHover : c.primary) : pressed ? c.divider : c.surface,
      })}
    >
      {icone ? icone(couleur) : null}
      <Text couleur={couleur} style={{ fontSize: 14, fontWeight: "700" }}>{titre}</Text>
      {retirable ? <X size={14} color={couleur} /> : null}
    </Pressable>
  );
}
