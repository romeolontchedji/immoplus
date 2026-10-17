import { useEffect, useState, useSyncExternalStore } from "react";
import { Animated, Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Bell, MessageCircle } from "lucide-react-native";
import { useSession } from "@/state/session";
import { Text } from "@/ui/components/Text";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { annonces } from "./annonces";
import { destination } from "./routage";

/**
 * Bannière interne discrète quand l'application est ouverte (plan v2, N5) : alimentée par l'événement temps réel
 * `notification.new` (donc aussi sous Expo Go), jamais pour la conversation déjà à l'écran. 4 s, appui = ouvrir.
 */
export function BanniereInterne() {
  const router = useRouter();
  const { role } = useSession();
  const haut = useSafeAreaInsets().top;
  const annonce = useSyncExternalStore(annonces.abonner, annonces.lire);
  const [position] = useState(() => new Animated.Value(-140));

  useEffect(() => {
    if (!annonce) return;
    Animated.spring(position, { toValue: 0, useNativeDriver: true, friction: 8 }).start();
    const minuteur = setTimeout(() => {
      Animated.timing(position, { toValue: -140, duration: 200, useNativeDriver: true }).start(() => annonces.changer(null));
    }, 4000);
    return () => clearTimeout(minuteur);
  }, [annonce, position]);

  if (!annonce) return null;
  const Icone = annonce.kind.startsWith("message") ? MessageCircle : Bell;
  return (
    <Animated.View pointerEvents="box-none" style={{ position: "absolute", top: haut + sp[2], left: sp[3], right: sp[3], transform: [{ translateY: position }] }}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${annonce.titre}. ${annonce.corps}`}
        onPress={() => {
          annonces.changer(null);
          router.push(destination(annonce.kind, annonce.data, role));
        }}
        style={{ flexDirection: "row", alignItems: "center", gap: sp[3], padding: sp[3], borderRadius: rayon.card, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.divider, ...ombre.pop }}
      >
        <View style={{ width: 36, height: 36, borderRadius: 12, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center" }}>
          <Icone size={18} color={colors.primary} />
        </View>
        <View style={{ flex: 1 }}>
          <Text variante="corpsGras" numberOfLines={1}>{annonce.titre}</Text>
          <Text variante="legende" muted numberOfLines={2}>{annonce.corps}</Text>
        </View>
      </Pressable>
    </Animated.View>
  );
}
