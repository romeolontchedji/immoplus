import { Stack } from "expo-router";

/** Écrans d'une annonce existante (fiche gérant, modification, statistiques), avec barre de retour. */
export default function AnnonceLayout() {
  return (
    <Stack screenOptions={{ headerShown: true, headerBackTitle: "Retour", headerShadowVisible: false }}>
      <Stack.Screen name="[id]/index" options={{ title: "Ma chambre" }} />
      <Stack.Screen name="[id]/modifier" options={{ title: "Modifier" }} />
      <Stack.Screen name="[id]/stats" options={{ title: "Statistiques" }} />
    </Stack>
  );
}
