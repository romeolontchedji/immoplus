import { Redirect, Stack } from "expo-router";
import { AuthFlowProvider } from "@/features/auth/flow";
import { useSession } from "@/state/session";

/** Écrans sans session : connexion, inscription, mot de passe oublié, présentation du compte gérant. Une session ouverte renvoie vers son espace. */
export default function AuthLayout() {
  const { etat, role } = useSession();
  if (etat.statut === "connecte") return <Redirect href={role === "gerant" ? "/pro/tableau-de-bord" : "/"} />;
  return (
    <AuthFlowProvider>
      <Stack screenOptions={{ headerShown: true, headerBackTitle: "Retour", title: "" }}>
        <Stack.Screen name="compte-gerant" options={{ headerShown: false }} />
        <Stack.Screen name="presentation" options={{ headerShown: false }} />
        <Stack.Screen name="bienvenue" options={{ headerShown: false }} />
      </Stack>
    </AuthFlowProvider>
  );
}
