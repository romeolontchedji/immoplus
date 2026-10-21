import { StyleSheet, View } from "react-native";
import Svg, { Circle, Path } from "react-native-svg";
import { colors } from "@/ui/theme/tokens";

/**
 * Motif de fond de marque (plan d'actions v2, P1.2 ; CDC §9.3 point 1) : courbes douces ponctuées de points cobalt et
 * soleil, en filigrane (opacité ≤ 8 %). Même dessin que `serveur/web/static/design/motif.svg`.
 * `sombre` : traits blancs, pour une carte cobalt ou nuit.
 */
export function FondMotif({ sombre = false, opacite = 0.08 }: { sombre?: boolean; opacite?: number }) {
  const trait = sombre ? colors.white : colors.blue;
  const point = sombre ? colors.white : colors.sun;
  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, { opacity: sombre ? opacite * 1.6 : opacite, overflow: "hidden" }]}>
      <Svg width="100%" height="100%" viewBox="0 0 400 400" preserveAspectRatio="xMidYMid slice">
        <Path d="M-20 90 C 60 40, 140 140, 220 90 S 380 40, 440 90" stroke={trait} strokeWidth={3} fill="none" strokeLinecap="round" />
        <Path d="M-20 250 C 80 200, 160 300, 260 250 S 400 200, 440 250" stroke={trait} strokeWidth={3} fill="none" strokeLinecap="round" />
        <Path d="M300 -10 L 420 110 M330 -10 L 440 100 M-10 330 L 90 430 M-10 360 L 60 430" stroke={trait} strokeWidth={10} strokeLinecap="round" opacity={0.6} />
        {[30, 110, 190, 270, 350].map((x, i) => (
          <Circle key={`h${x}`} cx={x} cy={i % 2 ? 72 : 108} r={5} fill={i % 2 ? point : trait} />
        ))}
        {[60, 140, 220, 300, 380].map((x, i) => (
          <Circle key={`b${x}`} cx={x} cy={i % 2 ? 232 : 268} r={5} fill={i % 2 ? trait : point} />
        ))}
        <Circle cx={340} cy={330} r={46} stroke={point} strokeWidth={3} fill="none" />
        <Circle cx={70} cy={170} r={22} stroke={trait} strokeWidth={3} fill="none" />
      </Svg>
    </View>
  );
}
