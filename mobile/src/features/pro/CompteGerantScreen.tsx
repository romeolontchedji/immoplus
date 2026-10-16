import { Linking, Pressable, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft, Check } from "lucide-react-native";
import { colors, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Text } from "@/ui/components/Text";

/**
 * CompteGerantScreen conforme à la maquette Mobile · Compte gérant@1x.png :
 * - En-tête : Flèche retour circulaire + "Compte gérant"
 * - Badge carré vert pâle avec coche ✓
 * - Titre : "Un compte gérant se mérite, et ça rassure tes futurs locataires."
 * - Sous-titre : pas d'inscription automatique (protège les locataires, valorise le badge Vérifié)
 * - Carte blanche 4 étapes numérotées
 * - Note sur les identifiants transmis par l'administrateur, puis bouton « J'ai déjà un compte, me connecter »
 * - Boutons « Écrire sur WhatsApp » et « Appeler +229 01 56 20 14 00 ».
 */
export function CompteGerantScreen() {
  const router = useRouter();
  const etapes = [
    {
      num: 1,
      titre: "Contacte-nous",
      desc: "Par WhatsApp ou appel.",
    },
    {
      num: 2,
      titre: "Fournis tes pièces",
      desc: "Pièce d’identité et justificatif d’activité.",
    },
    {
      num: 3,
      titre: "Court entretien",
      desc: "Pour valider que tu es un vrai gérant.",
    },
    {
      num: 4,
      titre: "L’équipe crée ton compte",
      desc: "Tu reçois tes identifiants, puis tu te connectes.",
    },
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
          Compte gérant
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={{
          padding: sp[4],
          gap: sp[4],
          paddingBottom: 40,
        }}
      >
        {/* Badge carré vert avec coche */}
        <View
          style={{
            width: 52,
            height: 52,
            borderRadius: 16,
            backgroundColor: "#DCFCE7",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Check size={26} color="#15803D" strokeWidth={3} />
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
            Un compte gérant se mérite, et ça rassure tes futurs locataires.
          </Text>

          <Text style={{ fontSize: 15, color: colors.textMuted, lineHeight: 22 }}>
            Pas d’inscription automatique : c’est ce qui protège les locataires et donne de la valeur
            à ton badge Vérifié.
          </Text>
        </View>

        {/* Carte blanche avec les 4 étapes */}
        <View
          style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 24,
            padding: sp[4],
            gap: sp[4],
            borderWidth: 1,
            borderColor: "rgba(15, 27, 61, 0.06)",
            shadowColor: colors.night,
            shadowOffset: { width: 0, height: 2 },
            shadowOpacity: 0.04,
            shadowRadius: 10,
            elevation: 1,
          }}
        >
          {etapes.map((e) => (
            <View key={e.num} style={{ flexDirection: "row", gap: 14, alignItems: "flex-start" }}>
              <View
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 18,
                  backgroundColor: "#EFF4FF",
                  justifyContent: "center",
                  alignItems: "center",
                  marginTop: 2,
                }}
              >
                <Text style={{ fontSize: 16, fontWeight: "800", color: colors.primary }}>
                  {e.num}
                </Text>
              </View>

              <View style={{ flex: 1, gap: 2 }}>
                <Text style={{ fontSize: 16, fontWeight: "700", color: colors.night }}>
                  {e.titre}
                </Text>
                <Text style={{ fontSize: 14, color: colors.textMuted, lineHeight: 20 }}>
                  {e.desc}
                </Text>
              </View>
            </View>
          ))}
        </View>

        <Text variante="legende" muted>
          Une fois le compte créé, l’équipe Logeo te transmet tes identifiants : connecte-toi avec
          ton numéro et ton mot de passe.
        </Text>

        {/* Actions directes */}
        <View style={{ gap: 12, marginTop: sp[3] }}>
          <Button
            titre="J'ai déjà un compte, me connecter"
            variante="secondaire"
            onPress={() => router.push("/connexion")}
          />

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Écrire sur WhatsApp"
            onPress={() => void Linking.openURL("https://wa.me/2290156201400")}
            style={{
              minHeight: 52,
              borderRadius: 16,
              backgroundColor: "#0D7A57",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: "700", color: "#FFFFFF" }}>
              Écrire sur WhatsApp
            </Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Appeler le numéro"
            onPress={() => void Linking.openURL("tel:+2290156201400")}
            style={{
              minHeight: 52,
              borderRadius: 16,
              backgroundColor: "#FFFFFF",
              borderWidth: 1.5,
              borderColor: colors.primary,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Text style={{ fontSize: 15, fontWeight: "700", color: colors.primary }}>
              Appeler +229 01 56 20 14 00
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </View>
  );
}
