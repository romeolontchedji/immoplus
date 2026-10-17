import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, type Href } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Pressable, TextInput, View } from "react-native";
import type { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { colors, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useAuthFlow } from "./flow";
import { useDemanderCode, useVerifierCode, type Objet } from "./hooks";
import { codeSchema } from "./schemas";

/**
 * Deuxième étape conforme à la maquette Mobile · Inscription 2 2@1x.png :
 * - En-tête : Logo Logeo à gauche, "Étape 2/2" à droite, barre de progression 2 segments bleus
 * - Titre "Entre le code reçu par SMS" + numéro formaté
 * - Boîtes de code individuelles avec bordure bleue active
 * - Compteur "Renvoyer le code dans MM:SS"
 * - Carte informative bleue "Ensuite, ta première alerte"
 * - Bouton primaire cobalt "Créer mon compte" / "Continuer"
 * - Bouton "Modifier mon numéro".
 */
export function CodeStep({
  objet,
  suivant,
  delaiRenvoiS = 60,
}: {
  objet: Objet;
  suivant: Href;
  delaiRenvoiS?: number;
}) {
  const router = useRouter();
  const flow = useAuthFlow();
  const verifier = useVerifierCode(objet);
  const renvoyer = useDemanderCode(objet);
  const [reste, setReste] = useState(delaiRenvoiS);
  const inputRef = useRef<TextInput>(null);

  const {
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<z.infer<typeof codeSchema>>({
    resolver: zodResolver(codeSchema),
    defaultValues: { code: "" },
  });

  const codeValue = watch("code") || "";

  useEffect(() => {
    if (reste <= 0) return;
    const m = setTimeout(() => setReste((r) => r - 1), 1000);
    return () => clearTimeout(m);
  }, [reste]);

  const erreur = verifier.error ?? renvoyer.error;
  const minutes = Math.floor(reste / 60);
  const secondes = reste % 60;
  const chrono = `${String(minutes).padStart(2, "0")}:${String(secondes).padStart(2, "0")}`;

  const estInscription = objet === "signup";

  return (
    <Screen scroll>
      <View style={{ gap: sp[4], paddingTop: sp[2], paddingBottom: sp[6] }}>
        {/* En-tête : Logo + Étape 2/2 */}
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <Logotype taille={38} />

          {estInscription ? (
            <Text style={{ fontSize: 13, fontWeight: "700", color: colors.textMuted }}>
              Étape 2/2
            </Text>
          ) : null}
        </View>

        {/* Barre de progression 2 segments (tous deux cobalt) */}
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
                backgroundColor: colors.primary,
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
            Entre le code reçu par SMS
          </Text>
          <Text style={{ fontSize: 15, color: colors.textMuted, lineHeight: 22 }}>
            Envoyé au {flow.phone ?? "ton numéro"}. Il expire dans 5 minutes.
          </Text>
        </View>

        {/* Cases de code (4 à 6 chiffres selon le serveur) */}
        <Pressable
          onPress={() => inputRef.current?.focus()}
          style={{ flexDirection: "row", justifyContent: "center", gap: 10, marginVertical: sp[3] }}
        >
          {[0, 1, 2, 3, 4, 5].map((index) => {
            const char = codeValue[index] || "";
            const estActif = index === codeValue.length;
            const estRempli = !!char;
            return (
              <View
                key={index}
                style={{
                  width: 48,
                  height: 60,
                  borderRadius: 14,
                  backgroundColor: "#FFFFFF",
                  borderWidth: 2,
                  borderColor: estRempli || estActif ? colors.primary : "rgba(15, 27, 61, 0.12)",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <Text
                  style={{
                    fontSize: 24,
                    fontWeight: "800",
                    color: estRempli ? colors.primary : colors.night,
                  }}
                >
                  {char}
                </Text>
              </View>
            );
          })}
        </Pressable>

        {/* Saisie invisible sous-jacente pour l'accessibilité et le clavier */}
        <Controller
          control={control}
          name="code"
          render={({ field }) => (
            <TextInput
              ref={inputRef}
              keyboardType="number-pad"
              maxLength={6}
              autoComplete="sms-otp"
              textContentType="oneTimeCode"
              value={field.value}
              onChangeText={field.onChange}
              style={{ position: "absolute", opacity: 0, width: 1, height: 1 }}
            />
          )}
        />

        {errors.code ? (
          <Text style={{ textAlign: "center", color: colors.danger, fontSize: 12, fontWeight: "600" }}>
            {errors.code.message}
          </Text>
        ) : null}

        {/* Renvoyer le code dans chrono */}
        <View style={{ alignItems: "center" }}>
          {reste > 0 ? (
            <Text style={{ fontSize: 14, color: colors.textMuted }}>
              Renvoyer le code dans{" "}
              <Text style={{ fontWeight: "700", color: colors.night }}>{chrono}</Text>
            </Text>
          ) : (
            <Pressable
              disabled={renvoyer.isPending}
              onPress={() =>
                flow.phone &&
                renvoyer.mutate(flow.phone, {
                  onSuccess: (r) => setReste(r.resendAfterS),
                })
              }
            >
              <Text style={{ fontSize: 14, color: colors.primary, fontWeight: "700" }}>
                Renvoyer le code maintenant
              </Text>
            </Pressable>
          )}
        </View>

        {/* Carte informative ensuite, ta première alerte */}
        {estInscription ? (
          <View
            style={{
              backgroundColor: "#EFF4FF",
              borderRadius: 18,
              padding: 16,
              gap: 6,
              marginTop: sp[2],
            }}
          >
            <Text style={{ fontSize: 15, fontWeight: "800", color: colors.primary }}>
              Ensuite, ta première alerte
            </Text>
            <Text style={{ fontSize: 13, color: colors.night, lineHeight: 18 }}>
              Dis-nous ton quartier et ton budget : on te prévient dès qu’une chambre correspond.
            </Text>
          </View>
        ) : null}

        {erreur ? (
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
              {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}
            </Text>
          </View>
        ) : null}

        {/* Bouton de validation */}
        <Button
          titre={estInscription ? "Continuer" : t.commun.continuer}
          chargement={verifier.isPending}
          onPress={handleSubmit((v) => {
            if (!flow.phone) return;
            verifier.mutate(
              { phone: flow.phone, code: v.code },
              {
                onSuccess: (jeton) => {
                  flow.definirJeton(jeton);
                  router.push(suivant);
                },
              },
            );
          })}
          style={{ marginTop: sp[2] }}
        />

        {/* Bouton retour / modifier mon numéro */}
        <Pressable
          onPress={() => router.back()}
          style={{ alignItems: "center", paddingVertical: 10 }}
        >
          <Text style={{ fontSize: 14, color: colors.primary, fontWeight: "700" }}>
            Modifier mon numéro
          </Text>
        </Pressable>
      </View>
    </Screen>
  );
}
