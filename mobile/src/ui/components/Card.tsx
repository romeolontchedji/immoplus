import type { ReactNode } from "react";
import { View, type ViewProps } from "react-native";
import { ombre, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Text } from "./Text";

type CardProps = ViewProps & {
  children: ReactNode;
  survole?: boolean;
};

export function Card({ children, style, ...rest }: CardProps) {
  const { c } = useTheme();
  return (
    <View
      {...rest}
      style={[
        {
          backgroundColor: c.surface,
          borderRadius: rayon.card,
          borderWidth: 1,
          borderColor: c.border,
          overflow: "hidden",
          ...ombre.card,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export type TonBadge =
  | "neutre"
  | "marque"
  | "succes"
  | "avertissement"
  | "danger"
  | "information";

export function Badge({
  titre,
  ton = "neutre",
  style,
}: {
  titre: string;
  ton?: TonBadge;
  style?: ViewProps["style"];
}) {
  const { c } = useTheme();
  const stylesTon: Record<TonBadge, [string, string]> = {
    neutre: [c.surfaceSunken, c.textMuted],
    marque: [c.primarySoft, c.primary],
    succes: [c.succesBg, c.succesText],
    avertissement: [c.avertissementBg, c.avertissementText],
    danger: [c.dangerBg, c.dangerText],
    information: [c.informationBg, c.informationText],
  };

  const [fond, texte] = stylesTon[ton];

  return (
    <View
      style={[
        {
          alignSelf: "flex-start",
          backgroundColor: fond,
          borderRadius: rayon.pilule,
          paddingHorizontal: sp[2] + 2,
          paddingVertical: sp[1],
        },
        style,
      ]}
    >
      <Text variante="legende" couleur={texte} style={{ fontWeight: "700", fontSize: 12 }}>
        {titre}
      </Text>
    </View>
  );
}
