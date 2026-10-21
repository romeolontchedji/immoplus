import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import { t } from "@/i18n/fr";
import { useTheme } from "@/ui/theme/ThemeProvider";

type Icone = keyof typeof Ionicons.glyphMap;
const ICONES: Record<string, Icone> = { "tableau-de-bord": "speedometer-outline", annonces: "albums-outline", messages: "chatbubbles-outline", profil: "person-outline" };

/** Quatre onglets : Tableau de bord, Annonces, Messages, Profil (CDC §12.3). */
export default function OngletsGerant() {
  const { c } = useTheme();
  return (
    <Tabs screenOptions={({ route }) => ({
      headerShown: false, tabBarActiveTintColor: c.primary, tabBarInactiveTintColor: c.textMuted,
      tabBarStyle: { backgroundColor: c.surface, borderTopColor: c.border },
      tabBarIcon: ({ color, size }) => <Ionicons name={ICONES[route.name] ?? "ellipse-outline"} color={color} size={size} />,
    })}>
      <Tabs.Screen name="tableau-de-bord" options={{ title: t.onglets.tableau }} />
      <Tabs.Screen name="annonces" options={{ title: t.onglets.annonces }} />
      <Tabs.Screen name="messages" options={{ title: t.onglets.messages }} />
      <Tabs.Screen name="profil" options={{ title: t.onglets.profil }} />
    </Tabs>
  );
}
