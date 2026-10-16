import { EmptyState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/**
 * SQUELETTE — Détail d'une annonce (gérant)
 *
 * Route    : /pro/annonce/[id]
 * API      : GET /v1/pro/listings/{id} ; POST …/confirm|hide|mark-rented|undo-rented|publish
 * États    : motifs de non-publiabilité (`manques`) ; confirmation avant « Louée » ; annulation possible 7 jours
 * Réf. CDC : EF-ANN-09 à EF-ANN-14
 *
 * À faire : remplacer le contenu par l'écran réel. Les crochets de données vont dans `queries.ts` de la fonctionnalité ;
 * les composants communs (`Screen`, `Button`, `TextField`, `QueryState`…) sont dans `src/ui/components`.
 */
export function AnnonceGerantScreen() {
  return (
    <Screen scroll>
      <Text variante="titre">{"Détail d'une annonce (gérant)"}</Text>
      <EmptyState titre="Écran à construire" texte="Statut, actions de cycle de vie, accès à la modification." />
    </Screen>
  );
}
