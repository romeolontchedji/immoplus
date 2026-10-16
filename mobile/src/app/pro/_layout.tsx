import { Redirect, Stack } from "expo-router";
import { useSession } from "@/state/session";

/** Espace gérant : compte gérant uniquement. Sans session → connexion ; compte locataire → espace locataire. */
export default function ProLayout() {
  const { etat, role } = useSession();
  if (etat.statut === "chargement") return null;
  if (etat.statut === "deconnecte") return <Redirect href="/connexion" />;
  if (role !== "gerant") return <Redirect href="/" />;
  return <Stack screenOptions={{ headerShown: false }} />;
}
