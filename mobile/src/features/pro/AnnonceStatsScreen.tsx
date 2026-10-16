import { EmptyState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/**
 * SQUELETTE — Statistiques d'une annonce
 *
 * Route    : /pro/annonce/[id]/stats
 * API      : (aucun point d'entrée serveur pour l'instant — voir docs/a-verifier.md)
 * États    : afficher les totaux du tableau de bord en attendant
 * Réf. CDC : EF-DSH-04
 *
 * À faire : remplacer le contenu par l'écran réel. Les crochets de données vont dans `queries.ts` de la fonctionnalité ;
 * les composants communs (`Screen`, `Button`, `TextField`, `QueryState`…) sont dans `src/ui/components`.
 */
export function AnnonceStatsScreen() {
  return (
    <Screen scroll>
      <Text variante="titre">{"Statistiques d'une annonce"}</Text>
      <EmptyState titre="Écran à construire" texte="Vues, favoris, conversations pour une annonce." />
    </Screen>
  );
}
