import { Pressable, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { Bell, Search } from "lucide-react-native";
import { colors, sp } from "@/ui/theme/tokens";
import { Chip } from "@/ui/components/Chip";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { FILTRES_VIDES, useFiltres } from "./filtres";
import { ListeAnnonces } from "./ListeAnnonces";
import { useFil } from "./queries";

/**
 * AccueilScreen conforme à la maquette Mobile · Accueil@1x.png :
 * - En-tête : Logo Logeo à gauche, bouton cloche notifications à droite
 * - Titre héroïque : "Où veux-tu habiter ?"
 * - Barre de recherche avec bouton bleu "Filtres"
 * - Chips raccourcis horizontaux (Près de l'UP, ≤ 15 000 F, Entrée-coucher...)
 * - Fil des annonces avec ListingCard fidèle.
 */
export function AccueilScreen() {
  const router = useRouter();
  const { filtres, definir } = useFiltres();
  const requete = useFil(filtres);

  const estActifDistance = filtres.sort === "distance";
  const estActifBudget15k = filtres.rent_max === 15000;
  const estActifEntreeCoucher = Array.isArray(filtres.type) && filtres.type.includes("entree_coucher");
  const estActifDouche = filtres.bathroom === true;

  return (
    <Screen flush>
      <ListeAnnonces
        requete={requete}
        vide={{
          titre: "Aucune chambre trouvée",
          texte: "Essaie d'élargir tes critères ou crée une alerte pour être prévenu.",
          action: "Créer une alerte",
          onAction: () => router.push("/nouvelle-alerte"),
        }}
        enTete={
          <View style={{ gap: sp[4], paddingBottom: sp[3], paddingTop: sp[2] }}>
            {/* Barre haute : Logo + Cloche de notification */}
            <View
              style={{
                flexDirection: "row",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <View
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 12,
                    backgroundColor: colors.primary,
                    justifyContent: "center",
                    alignItems: "center",
                  }}
                >
                  <Text style={{ color: "#FFFFFF", fontSize: 20, fontWeight: "800" }}>⌂</Text>
                </View>
                <Text style={{ fontSize: 22, fontWeight: "800", color: colors.night }}>
                  Logeo<Text style={{ color: colors.sun }}>.</Text>
                </Text>
              </View>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Notifications"
                onPress={() => router.push("/notifications")}
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 22,
                  backgroundColor: "#FFFFFF",
                  justifyContent: "center",
                  alignItems: "center",
                  shadowColor: colors.night,
                  shadowOffset: { width: 0, height: 2 },
                  shadowOpacity: 0.08,
                  shadowRadius: 8,
                  elevation: 2,
                }}
              >
                <Bell size={20} color={colors.night} />
              </Pressable>
            </View>

            {/* Titre héroïque */}
            <Text
              style={{
                fontSize: 28,
                fontWeight: "800",
                color: colors.night,
                letterSpacing: -0.5,
              }}
            >
              Où veux–tu habiter ?
            </Text>

            {/* Barre de recherche avec bouton Filtres */}
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                backgroundColor: "#FFFFFF",
                borderRadius: 20,
                paddingHorizontal: sp[3],
                paddingVertical: 8,
                shadowColor: colors.night,
                shadowOffset: { width: 0, height: 2 },
                shadowOpacity: 0.06,
                shadowRadius: 10,
                elevation: 2,
              }}
            >
              <Pressable
                onPress={() => router.push("/recherche")}
                style={{ flex: 1, flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 6 }}
              >
                <Search size={18} color={colors.textMuted} />
                <Text style={{ fontSize: 15, color: colors.textMuted, fontWeight: "500" }}>
                  Quartier, prix, type...
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Ouvrir les filtres"
                onPress={() => router.push("/filtres")}
                style={{
                  backgroundColor: colors.primary,
                  paddingHorizontal: 16,
                  paddingVertical: 10,
                  borderRadius: 14,
                }}
              >
                <Text style={{ color: "#FFFFFF", fontSize: 14, fontWeight: "700" }}>Filtres</Text>
              </Pressable>
            </View>

            {/* Rangée horizontale de filtres rapides */}
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ gap: sp[2], paddingRight: sp[2] }}
            >
              <Chip
                titre="Près de l’UP"
                actif={estActifDistance}
                onPress={() =>
                  definir({ ...filtres, sort: estActifDistance ? "recent" : "distance" })
                }
              />
              <Chip
                titre="≤ 15 000 F"
                actif={estActifBudget15k}
                onPress={() =>
                  definir({ ...filtres, rent_max: estActifBudget15k ? undefined : 15000 })
                }
              />
              <Chip
                titre="Entrée–coucher"
                actif={estActifEntreeCoucher}
                onPress={() =>
                  definir({
                    ...filtres,
                    type: estActifEntreeCoucher ? [] : ["entree_coucher"],
                  })
                }
              />
              <Chip
                titre="Douche interne"
                actif={estActifDouche}
                onPress={() =>
                  definir({ ...filtres, bathroom: estActifDouche ? undefined : true })
                }
              />
            </ScrollView>
          </View>
        }
      />
    </Screen>
  );
}
