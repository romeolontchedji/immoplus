import { EmptyState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/**
 * SQUELETTE — Assistant — Équipements
 *
 * Route    : /pro/nouvelle-annonce/equipements
 * API      : POST /v1/pro/listings (crée le brouillon serveur quand `champsManquants()` est vide)
 * États    : douche interne, clôture, eau, compteur ; erreurs de champs du serveur réaffichées
 * Réf. CDC : EF-ANN-04
 *
 * À faire : remplacer le contenu par l'écran réel. Les crochets de données vont dans `queries.ts` de la fonctionnalité ;
 * les composants communs (`Screen`, `Button`, `TextField`, `QueryState`…) sont dans `src/ui/components`.
 */
export function EquipementsStep() {
  return (
    <Screen scroll>
      <Text variante="titre">Assistant — Équipements</Text>
      <EmptyState titre="Écran à construire" texte="Étape 3 sur 6 : création côté serveur." />
    </Screen>
  );
}
