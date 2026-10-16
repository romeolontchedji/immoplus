import { EmptyState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/**
 * SQUELETTE — Écrire au gérant
 *
 * Route    : /conversation/nouvelle?listing=… (modale)
 * API      : POST /v1/conversations
 * États    : message pré-rempli modifiable ; erreurs `contact_detected` (422), `listing_unavailable` ; succès → remplace par /conversation/[id]
 * Réf. CDC : EF-MSG-01, EF-MSG-12
 *
 * À faire : remplacer le contenu par l'écran réel. Les crochets de données vont dans `queries.ts` de la fonctionnalité ;
 * les composants communs (`Screen`, `Button`, `TextField`, `QueryState`…) sont dans `src/ui/components`.
 */
export function NouvelleConversationScreen() {
  return (
    <Screen scroll>
      <Text variante="titre">Écrire au gérant</Text>
      <EmptyState titre="Écran à construire" texte="Premier message (obligatoire) avec rappel de ne pas partager de coordonnées." />
    </Screen>
  );
}
