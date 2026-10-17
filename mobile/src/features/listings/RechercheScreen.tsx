import { ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { ArrowDownUp } from "lucide-react-native";
import { colors, sp } from "@/ui/theme/tokens";
import { BarreRecherche } from "@/ui/components/BarreRecherche";
import { Chip } from "@/ui/components/Chip";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { LIBELLES_TRI, nombreDeFiltres, useFiltres, type Filtres } from "./filtres";
import { FiltresActifs } from "./FiltresActifs";
import { ListeAnnonces } from "./ListeAnnonces";
import { useFil } from "./queries";

const TRIS = Object.keys(LIBELLES_TRI) as Filtres["sort"][];

/**
 * Onglet « Recherche » : saisie libre en direct (sans accents, tolérante aux fautes côté serveur), tri en pastilles,
 * filtres actifs retirables. La barre et les résultats restent visibles ensemble ; le vide propose une alerte.
 */
export function RechercheScreen() {
  const router = useRouter();
  const { filtres, definir } = useFiltres();
  const requete = useFil(filtres);
  const nb = nombreDeFiltres(filtres);

  return (
    <Screen flush>
      <View style={{ paddingHorizontal: sp[4], paddingTop: sp[3], paddingBottom: sp[2], gap: sp[3] }}>
        <Text variante="titre">Rechercher</Text>
        <BarreRecherche valeur={filtres.q} onRecherche={(q) => definir({ ...filtres, q })} onFiltres={() => router.push("/filtres")} nbFiltres={nb} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: sp[2], alignItems: "center", paddingRight: sp[2] }}>
          <ArrowDownUp size={18} color={colors.textMuted} accessibilityLabel="Trier" />
          {TRIS.map((tri) => (
            <Chip key={tri} titre={LIBELLES_TRI[tri]} actif={filtres.sort === tri} onPress={() => definir({ ...filtres, sort: tri })} />
          ))}
        </ScrollView>
        <FiltresActifs />
      </View>
      <ListeAnnonces
        requete={requete}
        vide={{
          titre: filtres.q ? `Aucun résultat pour « ${filtres.q} »` : "Aucune chambre ne correspond",
          texte: "Vérifie l'orthographe, retire un filtre ou crée une alerte : tu seras prévenu dès qu'une chambre correspond.",
          action: "Créer une alerte",
          onAction: () => router.push("/nouvelle-alerte"),
        }}
      />
    </Screen>
  );
}
