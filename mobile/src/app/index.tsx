import { useEffect, useState } from "react";
import { Redirect } from "expo-router";
import { useSession } from "@/state/session";
import { CLES_KV, kv } from "@/storage/kv";

/**
 * Route d'entrée de l'application :
 * - Si l'utilisateur est connecté :
 *   - rôle gérant -> redirection vers son tableau de bord (/pro/tableau-de-bord)
 *   - rôle locataire -> redirection vers le fil d'annonces (/(locataire)/(onglets))
 * - Si l'utilisateur n'est pas connecté :
 *   - En développement (__DEV__ === true) : affiche l'onboarding (/bienvenue) à chaque fois pour faciliter le travail et les tests
 *   - En production : affiche l'onboarding (/bienvenue) la première fois, puis ouvre directement l'accueil locataire (/(locataire)/(onglets))
 */
export default function Index() {
  const { etat, role } = useSession();
  const [onboardingVu, setOnboardingVu] = useState<boolean | null>(null);

  useEffect(() => {
    let ignore = false;
    void kv.get<boolean>(CLES_KV.onboardingVu).then((vu) => {
      if (!ignore) setOnboardingVu(Boolean(vu));
    });
    return () => {
      ignore = true;
    };
  }, []);

  if (etat.statut === "chargement" || onboardingVu === null) {
    return null;
  }

  if (etat.statut === "connecte") {
    return <Redirect href={role === "gerant" ? "/pro/tableau-de-bord" : "/(locataire)/(onglets)"} />;
  }

  // En dev, on redirige toujours vers /bienvenue pour pouvoir peaufiner l'écran facilement.
  // En prod, seulement si l'utilisateur ne l'a pas encore vu.
  const doitAfficherBienvenue = __DEV__ || !onboardingVu;

  if (doitAfficherBienvenue) {
    return <Redirect href="/presentation" />; // présentation en 4 étapes, puis bienvenue (M2)
  }

  return <Redirect href="/(locataire)/(onglets)" />;
}
