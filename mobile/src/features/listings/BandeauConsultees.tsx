import { Pressable, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import { Home } from "lucide-react-native";
import { francs } from "@/lib/format";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Text } from "@/ui/components/Text";
import { effacerConsultees, useConsultees } from "./consultees";

/** « Tu as regardé récemment » : les dernières fiches ouvertes sur cet appareil ; rien tant qu'il n'y en a pas. */
export function BandeauConsultees() {
  const router = useRouter();
  const liste = useConsultees();
  if (liste.length === 0) return null;
  return (
    <View style={{ gap: sp[2] }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}>
        <Text variante="sousTitre">Tu as regardé récemment</Text>
        <Pressable accessibilityRole="button" onPress={effacerConsultees} hitSlop={8}>
          <Text variante="legende" style={{ color: colors.primary }}>Effacer</Text>
        </Pressable>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: sp[3], paddingRight: sp[2] }}>
        {liste.map((c) => (
          <Pressable
            key={c.slug}
            accessibilityRole="button"
            accessibilityLabel={`${c.title}, ${francs(c.rent_amount)} par mois`}
            onPress={() => router.push({ pathname: "/annonces/[ident]", params: { ident: c.slug } })}
            style={{ width: 150, backgroundColor: colors.surface, borderRadius: rayon.card, overflow: "hidden", ...ombre.card }}
          >
            {c.image ? (
              <Image source={{ uri: c.image }} style={{ width: 150, height: 90 }} contentFit="cover" />
            ) : (
              <View style={{ width: 150, height: 90, backgroundColor: colors.blueSoft, justifyContent: "center", alignItems: "center" }}>
                <Home size={24} color={colors.primary} />
              </View>
            )}
            <View style={{ padding: sp[2], gap: 2 }}>
              <Text variante="legende" numberOfLines={1} style={{ fontWeight: "700", color: colors.night }}>{c.title}</Text>
              <Text variante="legende" style={{ color: colors.primary, fontWeight: "700" }}>{francs(c.rent_amount)}</Text>
              {c.district ? <Text variante="legende" muted numberOfLines={1}>{c.district}</Text> : null}
            </View>
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}
