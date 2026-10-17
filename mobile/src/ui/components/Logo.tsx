import { View } from "react-native";
import Svg, { Circle, Path, Rect } from "react-native-svg";
import { colors } from "@/ui/theme/tokens";
import { Text } from "./Text";

interface LogoProps {
  taille?: number;
}

/**
 * Logo Logeo SVG officiel strict conforme à `docs/design/assets/logo.svg` :
 * - Fond bleu cobalt (#1B44D6) avec coins arrondis (rx 14)
 * - Épingle de localisation blanche
 * - Maisonnette bleue (#1B44D6) au centre
 * - Pastille soleil jaune (#FFB429) en haut à droite
 */
export function LogoIcon({ taille = 44 }: LogoProps) {
  return (
    <Svg width={taille} height={taille} viewBox="0 0 48 48">
      <Rect width="48" height="48" rx="14" fill="#1B44D6" />
      <Path
        d="M24 9c-6.6 0-12 5.2-12 11.7C12 29 24 39 24 39s12-10 12-18.3C36 14.2 30.6 9 24 9z"
        fill="#FFFFFF"
      />
      <Path d="M17.5 21.5 24 16l6.5 5.5V28h-4v-4.5h-5V28h-4z" fill="#1B44D6" />
      <Circle cx="36" cy="11" r="4.5" fill="#FFB429" />
    </Svg>
  );
}

interface LogotypeProps {
  /** Côté de l'icône ; le mot « Logeo » suit la même échelle (38 → 22 pt, comme l'en-tête du site). */
  taille?: number;
  /** Texte blanc sur un fond nuit ou une bannière ; sinon texte nuit sur fond clair. */
  surFondSombre?: boolean;
}

/** Logotype complet du site (`web/base.html`) : icône officielle + « Logeo » + point solaire. Unique source du logo mobile. */
export function Logotype({ taille = 38, surFondSombre = false }: LogotypeProps) {
  return (
    <View
      style={{ flexDirection: "row", alignItems: "center", gap: Math.round(taille * 0.22) }}
      accessible
      accessibilityRole="image"
      accessibilityLabel="Logeo"
    >
      <LogoIcon taille={taille} />
      <Text style={{ fontSize: Math.round(taille * 0.58), fontWeight: "800", color: surFondSombre ? colors.white : colors.night }}>
        Logeo<Text style={{ fontSize: Math.round(taille * 0.58), fontWeight: "800", color: colors.sun }}>.</Text>
      </Text>
    </View>
  );
}
