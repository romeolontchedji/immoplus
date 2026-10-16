import { useState } from "react";
import { Alert, Pressable, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft } from "lucide-react-native";
import { colors, sp } from "@/ui/theme/tokens";
import { PhoneField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";

type Operateur = "mtn" | "moov" | "celtiis";

/**
 * PaiementMobileMoneyScreen conforme à la maquette Mobile · Paiement Mobile Money@1x.png :
 * - En-tête : Flèche retour + "Paiement"
 * - Récapitulatif : "Abonnement gérant" + "2 000 F"
 * - Sélecteur opérateur : MTN MoMo, Moov Money, Celtiis Cash
 * - Champ numéro Mobile Money avec +229
 * - Message d'information sur la validation par code secret
 * - Bouton primaire cobalt "Confirmer le paiement · 2 000 F"
 * - Mention "Paiement sécurisé".
 */
export function PaiementMobileMoneyScreen() {
  const router = useRouter();
  const [operateur, setOperateur] = useState<Operateur>("mtn");
  const [numero, setNumero] = useState("");
  const [enCours, setEnCours] = useState(false);

  const operatuers: { id: Operateur; nom: string; badge: string; bgBadge: string; colorBadge: string }[] = [
    { id: "mtn", nom: "MTN MoMo", badge: "MTN", bgBadge: "#FFCC00", colorBadge: "#000000" },
    { id: "moov", nom: "Moov Money", badge: "Moov", bgBadge: "#0055A5", colorBadge: "#FFFFFF" },
    { id: "celtiis", nom: "Celtiis Cash", badge: "Celtiis", bgBadge: "#0F1B3D", colorBadge: "#FFFFFF" },
  ];

  const handlePaiement = () => {
    setEnCours(true);
    setTimeout(() => {
      setEnCours(false);
      Alert.alert(
        "Paiement pris en compte",
        "Durant la phase de lancement, l'accès gérant est offert. Ton abonnement est activé !",
        [{ text: "Continuer", onPress: () => router.push("/pro/tableau-de-bord") }],
      );
    }, 1000);
  };

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

        <Text style={{ fontSize: 18, fontWeight: "700", color: colors.night }}>Paiement</Text>
      </View>

      <ScrollView
        contentContainerStyle={{
          padding: sp[4],
          gap: sp[4],
          paddingBottom: 40,
        }}
      >
        {/* Carte récapitulatif */}
        <View
          style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 20,
            padding: sp[4],
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
            shadowColor: colors.night,
            shadowOffset: { width: 0, height: 2 },
            shadowOpacity: 0.05,
            shadowRadius: 10,
            elevation: 1,
          }}
        >
          <View style={{ gap: 2 }}>
            <Text style={{ fontSize: 16, fontWeight: "700", color: colors.night }}>
              Abonnement gérant
            </Text>
            <Text style={{ fontSize: 13, color: colors.textMuted }}>
              1 mois · sans engagement
            </Text>
          </View>

          <Text style={{ fontSize: 20, fontWeight: "800", color: colors.primary }}>
            2 000 F
          </Text>
        </View>

        {/* Section OPÉRATEUR */}
        <View style={{ gap: 10 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: "800",
              color: colors.night,
              letterSpacing: 0.5,
              textTransform: "uppercase",
            }}
          >
            OPÉRATEUR
          </Text>

          <View style={{ flexDirection: "row", gap: 10 }}>
            {operatuers.map((op) => {
              const actif = operateur === op.id;
              return (
                <Pressable
                  key={op.id}
                  onPress={() => setOperateur(op.id)}
                  style={{
                    flex: 1,
                    backgroundColor: "#FFFFFF",
                    borderRadius: 16,
                    paddingVertical: 14,
                    paddingHorizontal: 8,
                    alignItems: "center",
                    gap: 8,
                    borderWidth: 2,
                    borderColor: actif ? colors.primary : "rgba(15, 27, 61, 0.1)",
                  }}
                >
                  <View
                    style={{
                      paddingHorizontal: 8,
                      paddingVertical: 3,
                      borderRadius: 6,
                      backgroundColor: op.bgBadge,
                    }}
                  >
                    <Text style={{ fontSize: 11, fontWeight: "800", color: op.colorBadge }}>
                      {op.badge}
                    </Text>
                  </View>
                  <Text
                    style={{
                      fontSize: 12,
                      fontWeight: "700",
                      color: colors.night,
                      textAlign: "center",
                    }}
                  >
                    {op.nom}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        {/* Section NUMÉRO MOBILE MONEY */}
        <View style={{ gap: 6 }}>
          <PhoneField
            label="NUMÉRO MOBILE MONEY"
            value={numero}
            onChangeText={setNumero}
          />
        </View>

        {/* Encadré d'instruction bleu */}
        <View
          style={{
            backgroundColor: "#EFF4FF",
            borderRadius: 16,
            padding: 16,
          }}
        >
          <Text style={{ fontSize: 13, color: colors.primary, lineHeight: 18, fontWeight: "500" }}>
            Tu recevras une demande de confirmation sur ton téléphone. Valide avec ton code secret.
          </Text>
        </View>

        {/* Bouton de confirmation */}
        <View style={{ gap: 12, marginTop: sp[2] }}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Confirmer le paiement"
            disabled={enCours}
            onPress={handlePaiement}
            style={{
              minHeight: 52,
              borderRadius: 16,
              backgroundColor: colors.primary,
              justifyContent: "center",
              alignItems: "center",
              opacity: enCours ? 0.7 : 1,
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: "800", color: "#FFFFFF" }}>
              {enCours ? "Traitement..." : "Confirmer le paiement · 2 000 F"}
            </Text>
          </Pressable>

          <Text style={{ textAlign: "center", fontSize: 13, color: colors.textMuted }}>
            Paiement sécurisé
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}
