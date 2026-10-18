import { FlatList } from "react-native";
import { useRouter } from "expo-router";
import { sp } from "@/ui/theme/tokens";
import { EnTetePage } from "@/ui/components/EnTetePage";
import { Screen } from "@/ui/components/Screen";
import { ListingCard } from "@/ui/components/ListingCard";
import { QueryState } from "@/ui/components/States";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { useFavoris } from "./queries";

/** « Mes favoris » : une annonce devenue louée ou masquée reste affichée, avec son statut (le serveur la renvoie telle quelle). */
export function FavorisScreen() {
  const router = useRouter();
  const requete = useFavoris();
  return (
    <Screen flush>
      <AuthRequired>
        <QueryState query={requete} vide={{ quand: (l) => l.length === 0, titre: "Aucun favori", texte: "Touche le cœur d'une annonce pour la retrouver ici.", action: "Parcourir les chambres", onAction: () => router.push("/recherche") }}>
          {(liste) => <FlatList data={liste} keyExtractor={(a) => a.id} contentContainerStyle={{ padding: sp[4], gap: sp[4] }} ListHeaderComponent={<EnTetePage retour titre="Mes favoris" sousTitre="Les chambres que tu as gardées de côté." />} renderItem={({ item }) => <ListingCard annonce={item} favori onPress={() => router.push({ pathname: "/annonces/[ident]", params: { ident: item.slug } })} />} />}
        </QueryState>
      </AuthRequired>
    </Screen>
  );
}
