import { Stack } from "expo-router";

/** Écrans communs aux deux espaces, au-dessus des onglets : fiche, conversation, notifications, réglages, modales. */
export default function PartageLayout() {
  return (
    <Stack screenOptions={{ headerBackTitle: "Retour" }}>
      <Stack.Screen name="annonces/[ident]" options={{ title: "Annonce", headerShown: false }} />
      <Stack.Screen name="gerant/[id]" options={{ title: "Profil du gérant", headerShown: false }} />
      {/* L'écran dessine sa propre barre (nom, vérifié, menu) : pas d'en-tête natif qui laisserait un vide au-dessus */}
      <Stack.Screen name="conversation/[id]" options={{ title: "Conversation", headerShown: false }} />
      <Stack.Screen name="conversation/nouvelle" options={{ title: "Écrire au gérant", presentation: "modal" }} />
      <Stack.Screen name="notifications" options={{ title: "Notifications", headerShown: false }} />
      <Stack.Screen name="signaler" options={{ title: "Signaler", presentation: "modal" }} />
      <Stack.Screen name="legal/[slug]" options={{ title: "Informations légales", headerShown: false }} />
      <Stack.Screen name="filtres" options={{ title: "Filtres", presentation: "modal", headerShown: false }} />
    </Stack>
  );
}
