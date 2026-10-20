import { Pressable, View } from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";
import { colors, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Text } from "@/ui/components/Text";
import { CLES_KV, kv } from "@/storage/kv";

/**
 * BienvenueScreen conforme à la maquette Mobile · Bienvenue@1x.png :
 * - Partie haute : Dégradé bleu nuit immersif avec logo Immo+
 * - Feuille blanche inférieure arrondie (rayon 32)
 * - Titre : "Ta chambre à Parakou, vue en vidéo."
 * - Sous-titre : "Gérants vérifiés, alertes en temps réel, zéro arnaque."
 * - Pastilles douces : "Vérifiés", "Visite vidéo", "Alertes"
 * - CTA primaire bleu : "Je cherche une chambre"
 * - CTA secondaire crème : "Je suis gérant"
 * - Lien : "Déjà un compte ? Se connecter".
 */
export function BienvenueScreen() {
  const router = useRouter();

  return (
    <View style={{ flex: 1, backgroundColor: colors.night }}>
      {/* Moitié supérieure immersive : logo sur photo d'ambiance */}
      <View
        style={{
          flex: 1.1,
          backgroundColor: colors.night,
          paddingHorizontal: sp[4],
          paddingTop: 60,
          justifyContent: "space-between",
          paddingBottom: 20,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <Image
          source={require("../../../assets/photos/bienvenue.webp")}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
          }}
          contentFit="cover"
          accessibilityIgnoresInvertColors
        />
        {/* Voile : le logo reste lisible sur la photo (ADR 0006) */}
        <View style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(15, 27, 61, 0.45)" }} />

        {/* Logo Immo+ */}
        <Logotype taille={44} surFondSombre />
      </View>

      {/* Feuille blanche inférieure */}
      <View
        style={{
          flex: 1.4,
          backgroundColor: colors.white,
          borderTopLeftRadius: 32,
          borderTopRightRadius: 32,
          paddingHorizontal: sp[4],
          paddingTop: sp[5],
          paddingBottom: sp[5],
          justifyContent: "space-between",
        }}
      >
        <View style={{ gap: sp[3] }}>
          <Text
            style={{
              fontSize: 28,
              fontWeight: "800",
              color: colors.night,
              lineHeight: 34,
              letterSpacing: -0.5,
            }}
          >
            Ta chambre à Parakou, vue en vidéo.
          </Text>

          <Text style={{ fontSize: 15, color: colors.textMuted, lineHeight: 22 }}>
            Gérants vérifiés, alertes en temps réel, zéro arnaque.
          </Text>

          {/* Pastilles douces */}
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
            {["Vérifiés", "Visite vidéo", "Alertes"].map((item) => (
              <View
                key={item}
                style={{
                  backgroundColor: colors.blueSoft,
                  paddingHorizontal: 14,
                  paddingVertical: 7,
                  borderRadius: 999,
                }}
              >
                <Text style={{ color: colors.primary, fontSize: 13, fontWeight: "700" }}>
                  {item}
                </Text>
              </View>
            ))}
          </View>
        </View>

        {/* Boutons d'action */}
        <View style={{ gap: 12, marginTop: sp[3] }}>
          <Button
            titre="Je cherche une chambre"
            onPress={() => {
              void kv.set(CLES_KV.onboardingVu, true);
              router.replace("/(locataire)/(onglets)");
            }}
          />

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Je suis gérant"
            onPress={() => router.push("/compte-gerant")}
            style={{
              minHeight: 52,
              borderRadius: 16,
              backgroundColor: colors.warningBg,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: "700", color: colors.night }}>
              Je suis gérant
            </Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Se connecter"
            onPress={() => router.push("/connexion")}
            style={{ alignItems: "center", paddingVertical: 8 }}
          >
            <Text style={{ fontSize: 14, color: colors.night }}>
              Déjà un compte ?{" "}
              <Text style={{ color: colors.primary, fontWeight: "700" }}>Se connecter</Text>
            </Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}
