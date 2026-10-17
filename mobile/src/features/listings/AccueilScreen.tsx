import { Pressable, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { Bell } from "lucide-react-native";
import { colors, ombre, sp } from "@/ui/theme/tokens";
import { BarreRecherche } from "@/ui/components/BarreRecherche";
import { Chip } from "@/ui/components/Chip";
import { Logotype } from "@/ui/components/Logo";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { LIBELLES_TRI, nombreDeFiltres, useFiltres, type Filtres } from "./filtres";
import { BandeauConsultees } from "./BandeauConsultees";
import { FiltresActifs } from "./FiltresActifs";
import { ListeAnnonces } from "./ListeAnnonces";
import { useFil, useTypesChambre } from "./queries";

type Raccourci = { titre: string; actif: (f: Filtres) => boolean; basculer: (f: Filtres) => Filtres };

const basculerDans = (liste: string[], v: string) => (liste.includes(v) ? liste.filter((x) => x !== v) : [...liste, v]);

/** Raccourcis de la maquette : chacun s'ajoute aux autres critères au lieu de les écraser. */
const PRES_UP: Raccourci = { titre: "Près de l'UP", actif: (f) => f.sort === "distance", basculer: (f) => ({ ...f, sort: f.sort === "distance" ? "recent" : "distance" }) };
const BUDGET: Raccourci = { titre: "≤ 15 000 F", actif: (f) => f.rent_max === 15000, basculer: (f) => ({ ...f, rent_max: f.rent_max === 15000 ? undefined : 15000 }) };
const DOUCHE: Raccourci = { titre: "Douche interne", actif: (f) => f.bathroom === true, basculer: (f) => ({ ...f, bathroom: f.bathroom ? undefined : true }) };
const raccourciType = (slug: string, titre: string): Raccourci => ({ titre, actif: (f) => f.type.includes(slug), basculer: (f) => ({ ...f, type: basculerDans(f.type, slug) }) });

/**
 * Accueil locataire (maquette Mobile · Accueil) : logo + cloche, « Où veux-tu habiter ? », barre de recherche où l'on
 * tape directement (résultats en direct), raccourcis cumulables, filtres actifs retirables, puis le fil.
 */
export function AccueilScreen() {
  const router = useRouter();
  const { filtres, definir } = useFiltres();
  const requete = useFil(filtres);
  const types = useTypesChambre(); // les deux types les plus courants en raccourci (décision V1)
  const raccourcis = [PRES_UP, BUDGET, ...types.slice(0, 2).map((tp) => raccourciType(tp.slug, tp.label)), DOUCHE];
  const nb = nombreDeFiltres(filtres);
  const recherche = filtres.q.trim() !== "" || nb > 0;

  return (
    <Screen flush>
      <ListeAnnonces
        requete={requete}
        vide={{
          titre: "Aucune chambre trouvée",
          texte: recherche ? "Retire un filtre ou crée une alerte : tu seras prévenu dès qu'une chambre correspond." : "Les nouvelles chambres arrivent bientôt. Crée une alerte pour être prévenu.",
          action: "Créer une alerte",
          onAction: () => router.push("/nouvelle-alerte"),
        }}
        enTete={
          <View style={{ gap: sp[4], paddingBottom: sp[2], paddingTop: sp[2] }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
              <Logotype taille={38} />
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Notifications"
                onPress={() => router.push("/notifications")}
                style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: colors.surface, justifyContent: "center", alignItems: "center", ...ombre.card }}
              >
                <Bell size={20} color={colors.night} />
              </Pressable>
            </View>

            <Text style={{ fontSize: 28, lineHeight: 34, fontWeight: "800", color: colors.night, letterSpacing: -0.5 }}>Où veux-tu habiter ?</Text>

            <BarreRecherche
              valeur={filtres.q}
              onRecherche={(q) => definir({ ...filtres, q })}
              onFiltres={() => router.push("/filtres")}
              nbFiltres={nb}
            />

            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: sp[2], paddingRight: sp[2] }}>
              {raccourcis.map((r) => (
                <Chip key={r.titre} titre={r.titre} actif={r.actif(filtres)} onPress={() => definir(r.basculer(filtres))} />
              ))}
            </ScrollView>

            <FiltresActifs />

            {recherche ? null : <BandeauConsultees />}

            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", marginTop: sp[1] }}>
              <Text variante="sousTitre">{recherche ? "Résultats" : "Chambres disponibles"}</Text>
              <Text variante="legende" muted>{LIBELLES_TRI[filtres.sort]}</Text>
            </View>
          </View>
        }
      />
    </Screen>
  );
}
