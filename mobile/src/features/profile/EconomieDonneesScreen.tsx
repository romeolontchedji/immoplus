import { useCallback } from "react";
import { View } from "react-native";
import { CLES_KV, kv } from "@/storage/kv";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { Text } from "@/ui/components/Text";
import { usePreferences, useDefinirPreference } from "@/hooks/usePreferences";

/**
 * Économie de données (ENF-PERF-03) : interrupteur persistant dans AsyncStorage.
 * Quand activé, les vidéos ne se lancent pas automatiquement et le chargement différé des images est activé.
 */
export function EconomieDonneesScreen() {
  const { c } = useTheme();
  const prefs = usePreferences();
  const definir = useDefinirPreference();

  return (
    <Screen scroll>
      <Text variante="titre">Économie de données</Text>
      <Text muted>Réduis la consommation de données mobiles. Utile pour les connexions lentes ou les forfaits limités.</Text>
      <View
        style={{
          borderRadius: 16,
          borderWidth: 1,
          borderColor: c.border,
          backgroundColor: c.surface,
          paddingHorizontal: sp[4],
        }}
      >
        <SwitchRow
          titre="Économie de données"
          aide="Les vidéos ne se lisent qu'à l'appui. Les images se chargent progressivement."
          valeur={prefs.economieDonnees}
          onChange={(v) => definir("economieDonnees", v)}
        />
      </View>
      <View
        style={{
          padding: sp[4],
          borderRadius: 12,
          backgroundColor: c.primarySoft,
        }}
      >
        <Text variante="legende" couleur={c.primary}>
          Ce réglage est sauvegardé sur cet appareil uniquement. Il n'affecte pas les téléchargements en Wi-Fi.
        </Text>
      </View>
    </Screen>
  );
}
