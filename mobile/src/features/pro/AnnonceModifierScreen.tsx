import { EmptyState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/**
 * SQUELETTE — Modifier une annonce
 *
 * Route    : /pro/annonce/[id]/modifier
 * API      : PATCH /v1/pro/listings/{id}
 * États    : mêmes champs et validations que l'assistant ; `listing_locked` si modification impossible
 * Réf. CDC : EF-ANN-08
 *
 * À faire : remplacer le contenu par l'écran réel. Les crochets de données vont dans `queries.ts` de la fonctionnalité ;
 * les composants communs (`Screen`, `Button`, `TextField`, `QueryState`…) sont dans `src/ui/components`.
 */
export function AnnonceModifierScreen() {
  return (
    <Screen scroll>
      <Text variante="titre">Modifier une annonce</Text>
      <EmptyState titre="Écran à construire" texte="Édition d'une annonce existante." />
    </Screen>
  );
}
