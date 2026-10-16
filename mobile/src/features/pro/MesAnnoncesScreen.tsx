import { EmptyState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/**
 * SQUELETTE — Mes annonces
 *
 * Route    : /pro/annonces (onglet)
 * API      : GET /v1/pro/listings
 * États    : vide → « Créer une annonce » ; statuts (brouillon, en traitement, en ligne, masquée, louée) ; actions rapides
 * Réf. CDC : EF-ANN-01, EF-ANN-12
 *
 * À faire : remplacer le contenu par l'écran réel. Les crochets de données vont dans `queries.ts` de la fonctionnalité ;
 * les composants communs (`Screen`, `Button`, `TextField`, `QueryState`…) sont dans `src/ui/components`.
 */
export function MesAnnoncesScreen() {
  return (
    <Screen scroll>
      <Text variante="titre">Mes annonces</Text>
      <EmptyState titre="Écran à construire" texte="Liste par statut." />
    </Screen>
  );
}
