import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useRouter, type Href } from "expo-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Pressable, View } from "react-native";
import type { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { colors, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { PhoneField, TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { Check } from "lucide-react-native";
import { useAuthFlow } from "./flow";
import { useDemanderCode, type Objet } from "./hooks";
import { telephoneSchema } from "./schemas";

/**
 * Première étape conforme à la maquette Mobile · Inscription 1 2@1x.png :
 * - En-tête : Logo Logeo à gauche, "Étape 1/2" à droite, barre de progression 2 segments
 * - Titre : "Crée ton compte locataire"
 * - Champs Prénom et Numéro de téléphone (+229)
 * - Puces TU ES : "Étudiant(e) UP", "Étudiant(e) autre", "Autre"
 * - Case à cocher CGU
 * - Bouton "Recevoir le code" + lien connexion.
 */
export function TelephoneStep({
  objet,
  titre,
  consigne,
  suivant,
}: {
  objet: Objet;
  titre: string;
  consigne: string;
  suivant: Href;
}) {
  const router = useRouter();
  const flow = useAuthFlow();
  const demander = useDemanderCode(objet);
  const [prenom, setPrenom] = useState("");
  const [statutEtudiant, setStatutEtudiant] = useState<"up" | "autre" | "non">("up");
  const [cguAcceptees, setCguAcceptees] = useState(true);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<z.infer<typeof telephoneSchema>>({
    resolver: zodResolver(telephoneSchema),
    defaultValues: { phone: "" },
  });

  const estInscription = objet === "signup";

  return (
    <Screen scroll>
      <View style={{ gap: sp[4], paddingTop: sp[2], paddingBottom: sp[6] }}>
        {/* En-tête : Logo + Étape 1/2 */}
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
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

          {estInscription ? (
            <Text style={{ fontSize: 13, fontWeight: "700", color: colors.textMuted }}>
              Étape 1/2
            </Text>
          ) : null}
        </View>

        {/* Barre de progression 2 segments */}
        {estInscription ? (
          <View style={{ flexDirection: "row", gap: 8 }}>
            <View
              style={{
                flex: 1,
                height: 4,
                borderRadius: 2,
                backgroundColor: colors.primary,
              }}
            />
            <View
              style={{
                flex: 1,
                height: 4,
                borderRadius: 2,
                backgroundColor: "#E2E8F0",
              }}
            />
          </View>
        ) : null}

        {/* Titre et sous-titre */}
        <View style={{ gap: 6 }}>
          <Text
            style={{
              fontSize: 28,
              fontWeight: "800",
              color: colors.night,
              letterSpacing: -0.5,
            }}
          >
            {titre}
          </Text>
          <Text style={{ fontSize: 15, color: colors.textMuted, lineHeight: 22 }}>
            {consigne}
          </Text>
        </View>

        {/* Formulaire */}
        <View style={{ gap: sp[2] }}>
          {estInscription ? (
            <TextField
              label="PRÉNOM"
              placeholder="Awa"
              value={prenom}
              onChangeText={setPrenom}
            />
          ) : null}

          <Controller
            control={control}
            name="phone"
            render={({ field }) => (
              <PhoneField
                value={field.value}
                onChangeText={field.onChange}
                erreur={errors.phone?.message}
              />
            )}
          />

          {estInscription ? (
            <View style={{ gap: 8, marginTop: 4 }}>
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: "800",
                  color: colors.night,
                  letterSpacing: 0.5,
                  textTransform: "uppercase",
                }}
              >
                TU ES
              </Text>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                {[
                  { id: "up", label: "Étudiant(e) UP" },
                  { id: "autre", label: "Étudiant(e) autre" },
                  { id: "non", label: "Autre" },
                ].map((item) => {
                  const actif = statutEtudiant === item.id;
                  return (
                    <Pressable
                      key={item.id}
                      onPress={() => setStatutEtudiant(item.id as "up" | "autre" | "non")}
                      style={{
                        paddingHorizontal: 16,
                        paddingVertical: 10,
                        borderRadius: 999,
                        backgroundColor: actif ? colors.primary : "#FFFFFF",
                        borderWidth: 1.5,
                        borderColor: actif ? colors.primary : "rgba(15, 27, 61, 0.12)",
                      }}
                    >
                      <Text
                        style={{
                          fontSize: 14,
                          fontWeight: "700",
                          color: actif ? "#FFFFFF" : colors.night,
                        }}
                      >
                        {item.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
          ) : null}

          {estInscription ? (
            <Pressable
              onPress={() => setCguAcceptees(!cguAcceptees)}
              style={{
                flexDirection: "row",
                alignItems: "flex-start",
                gap: 12,
                marginTop: sp[3],
              }}
            >
              <View
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 6,
                  backgroundColor: cguAcceptees ? colors.primary : "#FFFFFF",
                  borderWidth: 1.5,
                  borderColor: cguAcceptees ? colors.primary : "rgba(15, 27, 61, 0.2)",
                  justifyContent: "center",
                  alignItems: "center",
                  marginTop: 2,
                }}
              >
                {cguAcceptees ? <Check size={14} color="#FFFFFF" strokeWidth={3} /> : null}
              </View>
              <Text style={{ flex: 1, fontSize: 13, color: colors.night, lineHeight: 18 }}>
                J’accepte les conditions d’utilisation et la politique de confidentialité de Logeo.
              </Text>
            </Pressable>
          ) : null}

          {estInscription ? (
            <Text
              style={{
                fontSize: 13,
                color: colors.textMuted,
                lineHeight: 18,
                marginTop: 4,
              }}
            >
              Inscription réservée aux locataires. Les comptes gérant sont créés par l’équipe Logeo.
            </Text>
          ) : null}

          {demander.error ? (
            <View
              style={{
                backgroundColor: "#FEE2E2",
                padding: 12,
                borderRadius: 12,
                marginTop: sp[2],
              }}
            >
              <Text
                style={{ color: "#DC2626", fontSize: 13, fontWeight: "600" }}
                accessibilityLiveRegion="polite"
              >
                {isApiError(demander.error)
                  ? messageErreur(demander.error.code, demander.error.message)
                  : t.erreurs.network}
              </Text>
            </View>
          ) : null}

          <Button
            titre="Recevoir le code"
            chargement={demander.isPending}
            onPress={handleSubmit((v) =>
              demander.mutate(v.phone, {
                onSuccess: (r) => {
                  flow.definirTelephone(r.phone);
                  router.push(suivant);
                },
              }),
            )}
            style={{ marginTop: sp[3] }}
          />
        </View>

        {/* Lien de connexion en bas */}
        <View style={{ alignItems: "center", marginTop: sp[2] }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <Text style={{ fontSize: 14, color: colors.night }}>Déjà un compte ?</Text>
            <Link href="/connexion">
              <Text style={{ fontSize: 14, color: colors.primary, fontWeight: "700" }}>
                Se connecter
              </Text>
            </Link>
          </View>
        </View>
      </View>
    </Screen>
  );
}
