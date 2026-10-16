import { Switch, View } from "react-native";
import { CIBLE_MIN, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Text } from "./Text";

export function SwitchRow({ titre, aide, valeur, onChange }: { titre: string; aide?: string; valeur: boolean; onChange: (v: boolean) => void }) {
  const { c } = useTheme();
  return (
    <View style={{ minHeight: CIBLE_MIN, flexDirection: "row", alignItems: "center", gap: sp[3] }}>
      <View style={{ flex: 1 }}>
        <Text>{titre}</Text>
        {aide ? <Text variante="legende" muted>{aide}</Text> : null}
      </View>
      <Switch accessibilityLabel={titre} value={valeur} onValueChange={onChange} trackColor={{ true: c.primary, false: c.borderStrong }} />
    </View>
  );
}
