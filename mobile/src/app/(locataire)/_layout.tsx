import { Redirect, Stack } from "expo-router";
import { useSession } from "@/state/session";

/** Espace locataire. Ouvert aux visiteurs (fil, recherche, fiches) ; un compte gérant est renvoyé vers son espace. */
export default function LocataireLayout() {
  const { role } = useSession();
  if (role === "gerant") return <Redirect href="/pro/tableau-de-bord" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}
