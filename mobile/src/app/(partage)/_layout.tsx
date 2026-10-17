import { Stack } from "expo-router";

/** Écrans communs aux deux espaces, au-dessus des onglets : fiche, conversation, notifications, réglages, modales. */
export default function PartageLayout() {
  return (
    <Stack screenOptions={{ headerBackTitle: "Retour" }}>
      <Stack.Screen name="annonces/[ident]" options={{ title: "Annonce", headerShown: false }} />
      <Stack.Screen name="conversation/[id]" options={{ title: "Conversation" }} />
      <Stack.Screen name="conversation/nouvelle" options={{ title: "Écrire au gérant", presentation: "modal" }} />
      <Stack.Screen name="notifications" options={{ title: "Notifications" }} />
      <Stack.Screen name="signaler" options={{ title: "Signaler", presentation: "modal" }} />
      <Stack.Screen name="legal/[slug]" options={{ title: "Informations légales", headerShown: false }} />
      <Stack.Screen name="filtres" options={{ title: "Filtres", presentation: "modal", headerShown: false }} />
    </Stack>
  );
}
