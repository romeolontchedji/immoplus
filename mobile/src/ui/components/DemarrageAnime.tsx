import { useEffect, useState } from "react";
import { Animated, Easing, StyleSheet, View } from "react-native";
import { colors } from "@/ui/theme/tokens";
import { LogoIcon } from "./Logo";

/**
 * Logo animé au démarrage (plan d'actions v2, M1) : suit l'écran natif blanc sans saut, l'épingle tombe, le mot
 * « Immo+ » apparaît, le point soleil pulse, puis tout s'efface. 1,2 s au total, `Animated` sans dépendance.
 */
export function DemarrageAnime({ onFin }: { onFin: () => void }) {
  const [chute] = useState(() => new Animated.Value(0));
  const [mot] = useState(() => new Animated.Value(0));
  const [point] = useState(() => new Animated.Value(1));
  const [sortie] = useState(() => new Animated.Value(1));

  useEffect(() => {
    Animated.sequence([
      Animated.spring(chute, { toValue: 1, useNativeDriver: true, friction: 6, tension: 90 }),
      Animated.parallel([
        Animated.timing(mot, { toValue: 1, duration: 260, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
        Animated.sequence([
          Animated.timing(point, { toValue: 1.6, duration: 160, useNativeDriver: true }),
          Animated.timing(point, { toValue: 1, duration: 160, useNativeDriver: true }),
        ]),
      ]),
      Animated.delay(120),
      Animated.timing(sortie, { toValue: 0, duration: 220, useNativeDriver: true }),
    ]).start(() => onFin());
  }, [chute, mot, point, sortie, onFin]);

  const translateY = chute.interpolate({ inputRange: [0, 1], outputRange: [-60, 0] });
  const scale = chute.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1] });

  return (
    <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, { backgroundColor: colors.white, alignItems: "center", justifyContent: "center", opacity: sortie }]}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
        <Animated.View style={{ transform: [{ translateY }, { scale }], opacity: chute }}>
          <LogoIcon taille={72} />
        </Animated.View>
        <Animated.Text style={{ fontSize: 40, fontWeight: "800", color: colors.night, opacity: mot, transform: [{ translateX: mot.interpolate({ inputRange: [0, 1], outputRange: [-12, 0] }) }] }}>
          Immo+
        </Animated.Text>
        <Animated.View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.sun, marginLeft: -10, marginTop: 22, opacity: mot, transform: [{ scale: point }] }} />
      </View>
    </Animated.View>
  );
}
