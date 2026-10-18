import { useRef, useState } from "react";
import { FlatList, Pressable, useWindowDimensions, View, type ImageSourcePropType, type ViewToken } from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { BellRing, MessageCircle, ShieldCheck, Video, type LucideIcon } from "lucide-react-native";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Text } from "@/ui/components/Text";
import { colors, rayon, sp } from "@/ui/theme/tokens";

type Etape = { icone: LucideIcon; titre: string; texte: string; teinte: string; photo: ImageSourcePropType };

const ETAPES: Etape[] = [
  { icone: Video, titre: "Des vraies chambres, en vidéo", texte: "Chaque annonce a une vidéo tournée sur place. Tu vois la chambre avant de te déplacer.", teinte: colors.blue, photo: require("../../../assets/photos/onboarding-2.webp") },
  { icone: ShieldCheck, titre: "Des gérants vérifiés", texte: "L'équipe Logeo vérifie l'identité de chaque gérant avant qu'il publie.", teinte: "#0E7C66", photo: require("../../../assets/photos/onboarding-4.webp") },
  { icone: MessageCircle, titre: "Discute directement avec le gérant", texte: "Écris-lui dans Logeo. Ton numéro reste privé tant que tu ne décides pas de le donner.", teinte: "#6A3FC8", photo: require("../../../assets/photos/onboarding-3.webp") },
  { icone: BellRing, titre: "Sois prévenu le premier", texte: "Crée une alerte : on te prévient dès qu'une chambre correspond à ton budget et à ton quartier.", teinte: "#B4471F", photo: require("../../../assets/photos/onboarding-1.webp") },
];

/**
 * Présentation en 4 étapes (plan d'actions v2, M2), avant l'écran de bienvenue : au premier lancement en production,
 * à chaque lancement en développement. Photo d'ambiance (ADR 0006) et pastille de l'étape dans sa teinte.
 */
export function PresentationScreen() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const liste = useRef<FlatList<Etape>>(null);
  const [index, setIndex] = useState(0);
  const derniere = index === ETAPES.length - 1;
  const terminer = () => router.replace("/bienvenue");
  const suivante = () => (derniere ? terminer() : liste.current?.scrollToIndex({ index: index + 1, animated: true }));
  // Fonction stable (FlatList refuse qu'elle change) : créée une fois, comme les valeurs animées.
  const [vues] = useState(() => ({ viewableItems }: { viewableItems: ViewToken[] }) => {
    const premier = viewableItems[0]?.index;
    if (typeof premier === "number") setIndex(premier);
  });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.white }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: sp[4], paddingVertical: sp[2] }}>
        <Logotype taille={32} />
        {derniere ? <View /> : (
          <Pressable accessibilityRole="button" onPress={terminer} hitSlop={12}>
            <Text variante="corpsGras" muted>Passer</Text>
          </Pressable>
        )}
      </View>

      <FlatList
        ref={liste}
        data={ETAPES}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        keyExtractor={(e) => e.titre}
        onViewableItemsChanged={vues}
        viewabilityConfig={{ itemVisiblePercentThreshold: 60 }}
        getItemLayout={(_, i) => ({ length: width, offset: width * i, index: i })}
        renderItem={({ item }) => {
          const Icone = item.icone;
          return (
            <View style={{ width, paddingHorizontal: sp[5], justifyContent: "center", gap: sp[6] }}>
              <View style={{ height: 300, borderRadius: rayon.sheet, backgroundColor: item.teinte, overflow: "hidden" }}>
                <Image source={item.photo} style={{ flex: 1 }} contentFit="cover" accessibilityIgnoresInvertColors />
                <View style={{ position: "absolute", left: sp[4], bottom: sp[4], width: 56, height: 56, borderRadius: 18, backgroundColor: item.teinte, alignItems: "center", justifyContent: "center" }}>
                  <Icone size={28} color={colors.white} strokeWidth={2} />
                </View>
              </View>
              <View style={{ gap: sp[3] }}>
                <Text variante="titre">{item.titre}</Text>
                <Text muted style={{ fontSize: 16, lineHeight: 24 }}>{item.texte}</Text>
              </View>
            </View>
          );
        }}
      />

      <View style={{ padding: sp[5], gap: sp[5] }}>
        <View style={{ flexDirection: "row", justifyContent: "center", gap: sp[2] }} accessibilityLabel={`Étape ${index + 1} sur ${ETAPES.length}`}>
          {ETAPES.map((e, i) => (
            <View key={e.titre} style={{ height: 8, width: i === index ? 24 : 8, borderRadius: 4, backgroundColor: i === index ? colors.primary : colors.border }} />
          ))}
        </View>
        <Button titre={derniere ? "Commencer" : "Suivant"} onPress={suivante} />
      </View>
    </SafeAreaView>
  );
}
