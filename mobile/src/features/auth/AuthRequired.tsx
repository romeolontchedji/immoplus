import { useRouter } from "expo-router";
import type { ReactNode } from "react";
import { t } from "@/i18n/fr";
import { EmptyState } from "@/ui/components/States";
import { useSession } from "@/state/session";

/** Les visiteurs sans compte parcourent le fil et les fiches ; les écrans personnels leur proposent de se connecter. */
export function AuthRequired({ children }: { children: ReactNode }) {
  const { etat } = useSession();
  const router = useRouter();
  if (etat.statut === "connecte") return <>{children}</>;
  return <EmptyState titre={t.commun.connexionRequise} texte="Crée un compte gratuit pour écrire aux gérants, enregistrer des favoris et créer des alertes." action={t.commun.seConnecter} onAction={() => router.push("/connexion")} />;
}
