import { Pressable, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft, Check } from "lucide-react-native";
import { colors, sp } from "@/ui/theme/tokens";
import { Text } from "@/ui/components/Text";

/**
 * AbonnementScreen conforme à la maquette Mobile · Abonnement@1x.png :
 * - En-tête : Flèche retour circulaire + "Abonnement gérant"
 * - Bandeau vert : "Gratuit pendant le lancement : tu ne paies rien pour l’instant."
 * - Titre : "Reste visible, publie en illimité"
 * - Sous-titre avec métriques de vues et contacts
 * - Carte offre Gérant (2 000 F/mois) avec bordure bleue cobalt et 4 points clés
 * - Mention "Tu ne paies que les mois où tu publies."
 * - CTA jaune solaire "Payer avec Mobile Money".
 */
export function AbonnementScreen() {
  const router = useRouter();

  const avantages = [
    "Chambres en illimité",
    "Mises en avant dans le fil",
    "Statistiques vues et contacts",
    "Badge Vérifié mis en avant",
  ];

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      {/* Barre supérieure */}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: 16,
          paddingHorizontal: sp[4],
          paddingTop: 54,
          paddingBottom: sp[3],
          backgroundColor: "#FFFFFF",
          borderBottomWidth: 1,
          borderBottomColor: "rgba(15, 27, 61, 0.06)",
        }}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Retour"
          onPress={() => router.back()}
          style={{
            width: 40,
            height: 40,
            borderRadius: 20,
            backgroundColor: "#F1F5F9",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <ArrowLeft size={20} color={colors.night} />
        </Pressable>

        <Text style={{ fontSize: 18, fontWeight: "700", color: colors.night }}>
          Abonnement gérant
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={{
          padding: sp[4],
          gap: sp[4],
          paddingBottom: 40,
        }}
      >
        {/* Bandeau vert gratuité lancement */}
        <View
          style={{
            backgroundColor: "#DCFCE7",
            borderRadius: 16,
            padding: 16,
          }}
        >
          <Text style={{ fontSize: 14, fontWeight: "700", color: "#166534", lineHeight: 20 }}>
            Gratuit pendant le lancement : tu ne paies rien pour l’instant.
          </Text>
        </View>

        {/* Titre et sous-titre */}
        <View style={{ gap: 8 }}>
          <Text
            style={{
              fontSize: 26,
              fontWeight: "800",
              color: colors.night,
              lineHeight: 32,
              letterSpacing: -0.5,
            }}
          >
            Reste visible, publie en illimité
          </Text>

          <Text style={{ fontSize: 15, color: colors.textMuted, lineHeight: 22 }}>
            Ce mois–ci, tes chambres ont été vues 240 fois et tu as reçu 12 contacts.
          </Text>
        </View>

        {/* Carte offre Gérant */}
        <View
          style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 24,
            padding: sp[4],
            gap: sp[4],
            borderWidth: 2,
            borderColor: colors.primary,
            shadowColor: colors.primary,
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.08,
            shadowRadius: 14,
            elevation: 2,
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
            <View>
              <Text style={{ fontSize: 20, fontWeight: "800", color: colors.night }}>Gérant</Text>
              <Text style={{ fontSize: 13, color: colors.textMuted }}>Sans engagement</Text>
            </View>

            <View style={{ alignItems: "flex-end" }}>
              <Text style={{ fontSize: 24, fontWeight: "800", color: colors.primary }}>
                2 000 F
              </Text>
              <Text style={{ fontSize: 12, color: colors.textMuted }}>/ mois</Text>
            </View>
          </View>

          <View style={{ gap: 12, paddingTop: 4 }}>
            {avantages.map((item) => (
              <View key={item} style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
                <Check size={18} color="#15803D" strokeWidth={3} />
                <Text style={{ fontSize: 15, fontWeight: "600", color: colors.night }}>
                  {item}
                </Text>
              </View>
            ))}
          </View>
        </View>

        {/* Note sous la carte */}
        <Text style={{ textAlign: "center", fontSize: 13, color: colors.textMuted }}>
          Tu ne paies que les mois où tu publies.
        </Text>

        {/* Bouton CTA jaune solaire */}
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Payer avec Mobile Money"
          onPress={() => router.push("/pro/paiement-mobile-money")}
          style={{
            minHeight: 52,
            borderRadius: 16,
            backgroundColor: colors.sun,
            justifyContent: "center",
            alignItems: "center",
            marginTop: sp[2],
          }}
        >
          <Text style={{ fontSize: 16, fontWeight: "800", color: colors.night }}>
            Payer avec Mobile Money
          </Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}
