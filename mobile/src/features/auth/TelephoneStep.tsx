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
import { PhoneField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { Check } from "lucide-react-native";
import { EnTeteEtapes } from "./EnTeteEtapes";
import { useAuthFlow } from "./flow";
import { useDemanderCode, type Objet } from "./hooks";
import { telephoneSchema } from "./schemas";

/**
 * Première étape d'un parcours à code (inscription, mot de passe oublié) : le numéro seulement.
 * Inscription : étape 1/2 et acceptation des conditions, active et jamais précochée, avant l'envoi du SMS.
 * Le nom et « Tu es » viennent à l'étape 2 (InscriptionProfilScreen), une seule fois (décision V2).
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
  const [cguAcceptees, setCguAcceptees] = useState(false); // acceptation active, jamais précochée

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
        <EnTeteEtapes {...(estInscription ? { etape: 1, total: 2 } : {})} />

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
            <Pressable
              onPress={() => setCguAcceptees(!cguAcceptees)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: cguAcceptees }}
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
                J’accepte les{" "}
                <Text style={{ fontSize: 13, color: colors.primary, fontWeight: "700" }} onPress={() => router.push("/legal/conditions")}>
                  conditions d’utilisation
                </Text>{" "}
                et la{" "}
                <Text style={{ fontSize: 13, color: colors.primary, fontWeight: "700" }} onPress={() => router.push("/legal/confidentialite")}>
                  politique de confidentialité
                </Text>{" "}
                de Logeo.
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
            disabled={estInscription && !cguAcceptees}
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
