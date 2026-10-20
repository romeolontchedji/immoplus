import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Pressable, View } from "react-native";
import type { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { colors, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { PasswordField, PhoneField } from "@/ui/components/TextField";
import { Logotype } from "@/ui/components/Logo";
import { Text } from "@/ui/components/Text";
import { useConnexion } from "./hooks";
import { connexionSchema } from "./schemas";

type Valeurs = z.infer<typeof connexionSchema>;

/**
 * ConnexionScreen fidèle à la maquette Mobile · Connexion@1x.png :
 * - Logo Immo+ avec puce solaire
 * - Titre "Entre ton numéro" + sous-titre
 * - Préfixe +229 et saisie du numéro
 * - Champ mot de passe avec affichage/masquage
 * - Bouton primaire cobalt "Se connecter"
 * - Liens "Mot de passe oublié ?" et "Pas de compte ? Inscris-toi"
 * - Mention d'information gérant en bas.
 */
export function ConnexionScreen() {
  const router = useRouter();
  const connexion = useConnexion();
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<Valeurs>({
    resolver: zodResolver(connexionSchema),
    defaultValues: { phone: "", password: "" },
  });

  const erreur = connexion.error;

  return (
    <Screen scroll>
      <View style={{ gap: sp[4], paddingTop: sp[2], paddingBottom: sp[6] }}>
        {/* Logo Immo+ */}
        <View style={{ marginBottom: sp[2] }}>
          <Logotype taille={38} />
        </View>

        {/* Titre et consigne */}
        <View style={{ gap: 6 }}>
          <Text
            style={{
              fontSize: 28,
              fontWeight: "800",
              color: colors.night,
              letterSpacing: -0.5,
            }}
          >
            Entre ton numéro
          </Text>
          <Text style={{ fontSize: 15, color: colors.textMuted, lineHeight: 22 }}>
            Connecte-toi pour retrouver tes alertes, tes favoris et tes conversations.
          </Text>
        </View>

        {/* Formulaire */}
        <View style={{ gap: sp[2], marginTop: sp[1] }}>
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

          <Controller
            control={control}
            name="password"
            render={({ field }) => (
              <PasswordField
                label="MOT DE PASSE"
                value={field.value}
                onChangeText={field.onChange}
                erreur={errors.password?.message}
              />
            )}
          />

          {erreur ? (
            <View
              style={{
                backgroundColor: colors.dangerBg,
                padding: 12,
                borderRadius: 12,
                marginBottom: sp[2],
              }}
            >
              <Text
                style={{ color: colors.danger, fontSize: 13, fontWeight: "600" }}
                accessibilityLiveRegion="polite"
              >
                {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}
              </Text>
            </View>
          ) : null}

          <Button
            titre={t.auth.seConnecter}
            chargement={connexion.isPending}
            onPress={handleSubmit((v) => connexion.mutate(v))}
            style={{ marginTop: sp[1] }}
          />

          {/* Lien mot de passe oublié */}
          <Pressable
            onPress={() => router.push("/mot-de-passe/telephone")}
            style={{ alignItems: "center", paddingVertical: 8 }}
          >
            <Text style={{ fontSize: 14, color: colors.primary, fontWeight: "600" }}>
              {t.auth.motDePasseOublie}
            </Text>
          </Pressable>
        </View>

        {/* Pied de page et liens d'inscription */}
        <View style={{ alignItems: "center", gap: 14, marginTop: sp[4] }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <Text style={{ fontSize: 14, color: colors.night }}>Pas de compte ?</Text>
            <Link href="/inscription/telephone">
              <Text style={{ fontSize: 14, color: colors.primary, fontWeight: "700" }}>
                Inscris–toi
              </Text>
            </Link>
          </View>

          <Text
            style={{
              fontSize: 13,
              color: colors.textMuted,
              textAlign: "center",
              lineHeight: 18,
              paddingHorizontal: sp[3],
            }}
          >
            L’inscription est réservée aux locataires. Les comptes gérant sont créés par l’équipe
            Immo+.
          </Text>
        </View>
      </View>
    </Screen>
  );
}
