import { ActivityIndicator, Pressable, type PressableProps } from "react-native";
import { CIBLE_MIN, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Text } from "./Text";

export type VarianteBouton = "primaire" | "secondaire" | "accent" | "fantome" | "danger";

type Props = Omit<PressableProps, "children"> & {
  titre: string;
  variante?: VarianteBouton;
  chargement?: boolean;
  taille?: "normale" | "compacte";
};

export function Button({
  titre,
  variante = "primaire",
  chargement = false,
  taille = "normale",
  disabled,
  style,
  ...rest
}: Props) {
  const { c } = useTheme();
  const inactif = disabled || chargement;

  // Règle d'or DESIGN.md :
  // - primaire = bleu cobalt #1B44D6 sur fond clair
  // - accent = jaune solaire #FFB429 sur fond sombre ou hero
  // - secondaire = surface blanche avec bordure #D5DAEA
  const fond = {
    primaire: c.primary,
    accent: c.accent,
    secondaire: c.surface,
    fantome: "transparent",
    danger: c.danger,
  }[variante];

  const couleurTexte = {
    primaire: c.onPrimary,
    accent: c.onAccent,
    secondaire: c.text,
    fantome: c.primary,
    danger: "#FFFFFF",
  }[variante];

  const hauteurMin = taille === "compacte" ? 40 : CIBLE_MIN;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inactif, busy: chargement }}
      disabled={inactif}
      {...rest}
      style={({ pressed }) => [
        {
          minHeight: hauteurMin,
          paddingHorizontal: taille === "compacte" ? sp[4] : sp[5],
          paddingVertical: sp[3],
          borderRadius: rayon.field,
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "row",
          gap: sp[2],
          backgroundColor: fond,
          borderWidth: variante === "secondaire" ? 1.5 : 0,
          borderColor: c.borderStrong,
          opacity: inactif ? 0.5 : pressed ? 0.88 : 1,
        },
        typeof style === "function" ? style({ pressed }) : style,
      ]}
    >
      {chargement ? <ActivityIndicator size="small" color={couleurTexte} /> : null}
      <Text
        variante="lien"
        couleur={couleurTexte}
        style={{ fontWeight: "700" }}
      >
        {titre}
      </Text>
    </Pressable>
  );
}
