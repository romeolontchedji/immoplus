import { ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { ArrowDownUp } from "lucide-react-native";
import { colors, sp } from "@/ui/theme/tokens";
import { BarreRecherche } from "@/ui/components/BarreRecherche";
import { EnTetePage } from "@/ui/components/EnTetePage";
import { Chip } from "@/ui/components/Chip";
import { ListeDeroulante } from "@/ui/components/ListeDeroulante";
import { Screen } from "@/ui/components/Screen";
import { LIBELLES_TRI, nombreDeFiltres, useFiltres, type Filtres } from "./filtres";
import { FiltresActifs } from "./FiltresActifs";
import { ListeAnnonces } from "./ListeAnnonces";
import { useDistricts, useFil, useTypesChambre } from "./queries";

const TRIS = Object.keys(LIBELLES_TRI) as Filtres["sort"][];

/**
 * Onglet « Recherche » : saisie libre en direct (sans accents, tolérante aux fautes côté serveur), quartier et type en
 * listes déroulantes appliquées tout de suite, tri en pastilles, filtres actifs retirables. Un quartier presque vide
 * propose à part les quartiers voisins ; le vide propose une alerte.
 */
export function RechercheScreen() {
  const router = useRouter();
  const { filtres, definir } = useFiltres();
  const requete = useFil(filtres);
  const nb = nombreDeFiltres(filtres);
  const districts = useDistricts();
  const types = useTypesChambre();

  return (
    <Screen flush>
      <View style={{ paddingHorizontal: sp[4], paddingTop: sp[3], paddingBottom: sp[2], gap: sp[3] }}>
        <EnTetePage titre="Rechercher" />
        <BarreRecherche valeur={filtres.q} onRecherche={(q) => definir({ ...filtres, q })} onFiltres={() => router.push("/filtres")} nbFiltres={nb} />
        {/* Filtres rapides, appliqués tout de suite (plan v3, A1 et A3) ; les autres sont dans « Filtres ». */}
        <View style={{ flexDirection: "row", gap: sp[3] }}>
          <View style={{ flex: 1 }}>
            <ListeDeroulante
              label="Quartier"
              placeholder="Tous"
              options={(districts.data ?? []).map((d) => ({ valeur: d.slug, libelle: d.name }))}
              valeurs={filtres.district.slice(0, 1)}
              onChange={(v) => definir({ ...filtres, district: v })}
            />
          </View>
          <View style={{ flex: 1 }}>
            <ListeDeroulante
              label="Type"
              placeholder="Tous"
              options={types.map((x) => ({ valeur: x.slug, libelle: x.label }))}
              valeurs={filtres.type.slice(0, 1)}
              onChange={(v) => definir({ ...filtres, type: v })}
            />
          </View>
        </View>
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
