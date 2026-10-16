import { Stack } from "expo-router";
import { BrouillonProvider } from "@/features/pro/brouillon";

/** Assistant de création : six étapes, brouillon local persisté (voir `features/pro/brouillon.tsx`). */
export default function NouvelleAnnonceLayout() {
  return (
    <BrouillonProvider>
      <Stack screenOptions={{ headerShown: true, headerBackTitle: "Retour" }}>
        <Stack.Screen name="infos" options={{ title: "1/6 · Infos" }} />
        <Stack.Screen name="localisation" options={{ title: "2/6 · Localisation" }} />
        <Stack.Screen name="equipements" options={{ title: "3/6 · Équipements" }} />
        <Stack.Screen name="medias" options={{ title: "4/6 · Photos et vidéo" }} />
        <Stack.Screen name="description" options={{ title: "5/6 · Description" }} />
        <Stack.Screen name="publication" options={{ title: "6/6 · Publication" }} />
      </Stack>
    </BrouillonProvider>
  );
}
