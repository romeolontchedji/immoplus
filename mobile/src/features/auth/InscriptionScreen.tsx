import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "expo-router";
import { useEffect, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { View } from "react-native";
import type { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { Logotype } from "@/ui/components/Logo";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { PasswordField, TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { colors, sp } from "@/ui/theme/tokens";
import { ChoixOccupation, type Occupation } from "./ChoixOccupation";
import { useDisponibilite, useInscription } from "./hooks";
import { inscriptionSchema } from "./schemas";

type Valeurs = z.input<typeof inscriptionSchema>;

/** Nom tapé, attendu un court instant avant d'interroger le serveur (pas une requête par lettre). */
function useDiffere(valeur: string, delai = 350) {
  const [differe, setDiffere] = useState(valeur);
  useEffect(() => {
    const minuteur = setTimeout(() => setDiffere(valeur), delai);
    return () => clearTimeout(minuteur);
  }, [valeur, delai]);
  return differe;
}

/**
 * Inscription sur un seul écran, sans code SMS ni numéro (ADR 0009) : prénom, nom, nom d'utilisateur (disponibilité
 * vérifiée pendant la frappe, avec des suggestions), « Tu es », mot de passe et conditions. La clé de secours
 * s'affiche juste après (`CleSecoursHote`).
 */
export function InscriptionScreen() {
  const inscription = useInscription();
  const [occupation, setOccupation] = useState<Occupation | null>(null);
  const { control, handleSubmit, setValue, formState: { errors } } = useForm<Valeurs>({
    resolver: zodResolver(inscriptionSchema),
    defaultValues: { first_name: "", last_name: "", username: "", password: "", terms_accepted: false as unknown as true },
  });
  const [prenom, nom, nomUtilisateur] = useWatch({ control, name: ["first_name", "last_name", "username"] });
  const tape = useDiffere((nomUtilisateur ?? "").trim().replace(/^@/, "").toLowerCase());
  const dispo = useDisponibilite(tape, prenom ?? "", nom ?? "");
  const verdict = tape.length >= 3 ? dispo.data : undefined;

  return (
    <Screen scroll>
      <View style={{ gap: sp[1], marginBottom: sp[2] }}>
        <Logotype taille={28} />
        <Text variante="titre" style={{ marginTop: sp[3] }}>Crée ton compte</Text>
        <Text muted>Sans code par SMS : ton nom d’utilisateur et ton mot de passe suffisent.</Text>
      </View>

      <View style={{ flexDirection: "row", gap: sp[3] }}>
        <View style={{ flex: 1 }}>
          <Controller control={control} name="first_name" render={({ field }) => (
            <TextField label="Prénom" autoCapitalize="words" autoComplete="given-name" textContentType="givenName" value={field.value} onChangeText={field.onChange} erreur={errors.first_name?.message} />
          )} />
        </View>
        <View style={{ flex: 1 }}>
          <Controller control={control} name="last_name" render={({ field }) => (
            <TextField label="Nom" autoCapitalize="words" autoComplete="family-name" textContentType="familyName" value={field.value} onChangeText={field.onChange} erreur={errors.last_name?.message} />
          )} />
        </View>
      </View>

      <Controller control={control} name="username" render={({ field }) => (
        <TextField
          label="Nom d’utilisateur"
          placeholder="awa.bio"
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="username-new"
          textContentType="username"
          value={field.value}
          onChangeText={field.onChange}
          erreur={errors.username?.message ?? (verdict && !verdict.available ? verdict.message : undefined)}
          aide={verdict?.available ? "Disponible." : "3 à 30 caractères : lettres, chiffres, point ou tiret bas. Il sert à te connecter."}
        />
      )} />
      {verdict && !verdict.available && verdict.suggestions.length ? (
        <View style={{ gap: sp[2], marginTop: -sp[2], marginBottom: sp[3] }}>
          <Text variante="legende" muted>Libres :</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
            {verdict.suggestions.map((s) => (
              <Chip key={s} titre={s} actif={false} onPress={() => setValue("username", s, { shouldValidate: true })} />
            ))}
          </View>
        </View>
      ) : null}

      <ChoixOccupation valeur={occupation} onChange={setOccupation} />
      <Controller control={control} name="password" render={({ field }) => (
        <PasswordField label={t.auth.motDePasse} value={field.value} onChangeText={field.onChange} erreur={errors.password?.message} aide="10 caractères au moins, différent de ton nom." />
      )} />
      <Controller control={control} name="terms_accepted" render={({ field }) => (
        <SwitchRow titre={t.auth.cgu} valeur={!!field.value} onChange={(v) => field.onChange(v)} />
      )} />
      {errors.terms_accepted ? <Text variante="legende" couleur={colors.danger}>{errors.terms_accepted.message}</Text> : null}

      {inscription.error ? (
        <Text couleur={colors.danger} accessibilityLiveRegion="polite">
          {isApiError(inscription.error) ? messageErreur(inscription.error.code, inscription.error.message) : t.erreurs.network}
        </Text>
      ) : null}
      <Button
        titre={t.auth.creerCompte}
        chargement={inscription.isPending}
        onPress={handleSubmit((v) => {
          const d = inscriptionSchema.parse(v);
          inscription.mutate({ first_name: d.first_name, last_name: d.last_name, username: d.username, password: d.password, occupation });
        })}
      />
      <View style={{ flexDirection: "row", justifyContent: "center", gap: 6, marginTop: sp[3] }}>
        <Text>Déjà un compte ?</Text>
        <Link href="/connexion"><Text style={{ color: colors.primary, fontWeight: "700" }}>Se connecter</Text></Link>
      </View>
    </Screen>
  );
}
