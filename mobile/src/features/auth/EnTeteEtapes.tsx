import { View } from "react-native";
import { Logotype } from "@/ui/components/Logo";
import { Text } from "@/ui/components/Text";
import { colors, sp } from "@/ui/theme/tokens";

/** Logo, « Étape n/total » et barre de progression des parcours en plusieurs écrans (inscription). */
export function EnTeteEtapes({ etape, total }: { etape?: number; total?: number }) {
  return (
    <View style={{ gap: sp[4] }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Logotype taille={30} />
        {etape && total ? <Text variante="legende" muted style={{ fontWeight: "700" }}>Étape {etape}/{total}</Text> : null}
      </View>
      {etape && total ? (
        <View style={{ flexDirection: "row", gap: sp[2] }} accessibilityLabel={`Étape ${etape} sur ${total}`}>
          {Array.from({ length: total }, (_, i) => (
            <View key={i} style={{ flex: 1, height: 4, borderRadius: 2, backgroundColor: i < etape ? colors.primary : colors.divider }} />
          ))}
        </View>
      ) : null}
    </View>
  );
}
