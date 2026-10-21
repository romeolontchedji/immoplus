import { useEffect, useState } from "react";
import { Animated, type DimensionValue } from "react-native";
import { rayon } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";

/** Squelette de chargement (CDC §12.1 : jamais d'écran vide pendant le chargement). */
export function Skeleton({ hauteur = 16, largeur = "100%" }: { hauteur?: number; largeur?: DimensionValue }) {
  const { c } = useTheme();
  const [opacite] = useState(() => new Animated.Value(0.5));
  useEffect(() => {
    const boucle = Animated.loop(Animated.sequence([
      Animated.timing(opacite, { toValue: 1, duration: 700, useNativeDriver: true }),
      Animated.timing(opacite, { toValue: 0.5, duration: 700, useNativeDriver: true }),
    ]));
    boucle.start();
    return () => boucle.stop();
  }, [opacite]);
  return <Animated.View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={{ height: hauteur, width: largeur, borderRadius: rayon[1], backgroundColor: c.border, opacity: opacite }} />;
}

export function SkeletonListe({ lignes = 4 }: { lignes?: number }) {
  return <>{Array.from({ length: lignes }, (_, i) => <Skeleton key={i} hauteur={88} />)}</>;
}
