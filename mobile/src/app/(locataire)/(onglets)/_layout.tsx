import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import { t } from "@/i18n/fr";
import { useNonLues } from "@/features/notifications/queries";
import { useSession } from "@/state/session";
import { useTheme } from "@/ui/theme/ThemeProvider";

type Icone = keyof typeof Ionicons.glyphMap;
const ICONES: Record<string, Icone> = { index: "home-outline", recherche: "search-outline", messages: "chatbubbles-outline", alertes: "notifications-outline", profil: "person-outline" };

/** Cinq onglets : Accueil, Recherche, Messages, Alertes, Profil (CDC §12.2). */
export default function OngletsLocataire() {
  const { c } = useTheme();
  const { etat } = useSession();
  const nonLues = useNonLues(etat.statut === "connecte").data?.unread_count;
  return (
    <Tabs screenOptions={({ route }) => ({
      headerShown: false, tabBarActiveTintColor: c.primary, tabBarInactiveTintColor: c.textMuted,
      tabBarStyle: { backgroundColor: c.surface, borderTopColor: c.border },
      tabBarIcon: ({ color, size }) => <Ionicons name={ICONES[route.name] ?? "ellipse-outline"} color={color} size={size} />,
    })}>
      <Tabs.Screen name="index" options={{ title: t.onglets.accueil }} />
      <Tabs.Screen name="recherche" options={{ title: t.onglets.recherche }} />
      <Tabs.Screen name="messages" options={{ title: t.onglets.messages }} />
      <Tabs.Screen name="alertes" options={{ title: t.onglets.alertes, tabBarBadge: nonLues ? (nonLues > 99 ? "99+" : nonLues) : undefined }} />
      <Tabs.Screen name="profil" options={{ title: t.onglets.profil }} />
    </Tabs>
  );
}
