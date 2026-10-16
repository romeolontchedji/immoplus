import { Text as RNText, type TextProps } from "react-native";
import { fs } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";

export type VarianteTexte =
  | "hero"
  | "titre"
  | "titreSection"
  | "sousTitre"
  | "corps"
  | "corpsGras"
  | "legende"
  | "label"
  | "prix"
  | "lien";

type Props = TextProps & {
  variante?: VarianteTexte;
  muted?: boolean;
  couleur?: string;
};

const styles: Record<
  VarianteTexte,
  {
    fontSize: number;
    fontWeight: "400" | "500" | "600" | "700" | "800";
    lineHeight: number;
    letterSpacing?: number;
    textTransform?: "uppercase" | "none";
  }
> = {
  hero: { fontSize: fs[30], fontWeight: "800", lineHeight: 36, letterSpacing: -0.8 },
  titre: { fontSize: fs[26], fontWeight: "800", lineHeight: 32, letterSpacing: -0.6 },
  titreSection: { fontSize: fs[20], fontWeight: "800", lineHeight: 26, letterSpacing: -0.4 },
  sousTitre: { fontSize: fs[18], fontWeight: "700", lineHeight: 24, letterSpacing: -0.2 },
  corps: { fontSize: fs[15], fontWeight: "500", lineHeight: 22 },
  corpsGras: { fontSize: fs[15], fontWeight: "700", lineHeight: 22 },
  legende: { fontSize: fs[13], fontWeight: "500", lineHeight: 18 },
  label: { fontSize: fs[12], fontWeight: "800", lineHeight: 16, letterSpacing: 0.6, textTransform: "uppercase" },
  prix: { fontSize: fs[20], fontWeight: "800", lineHeight: 26, letterSpacing: -0.4 },
  lien: { fontSize: fs[15], fontWeight: "700", lineHeight: 22 },
};

export function Text({ variante = "corps", muted, couleur, style, ...rest }: Props) {
  const { c } = useTheme();
  const color =
    couleur ??
    (variante === "lien"
      ? c.link
      : variante === "label" || muted
      ? c.textMuted
      : c.text);

  return <RNText {...rest} style={[styles[variante], { color }, style]} />;
}
