import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { View } from "react-native";
import type { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Screen } from "@/ui/components/Screen";
import { PasswordField, TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { sp, colors } from "@/ui/theme/tokens";
import { ChoixOccupation, type Occupation } from "./ChoixOccupation";
import { EnTeteEtapes } from "./EnTeteEtapes";
import { useAuthFlow } from "./flow";
import { useInscription, useReinitialiserMotDePasse } from "./hooks";
import { nouveauMotDePasseSchema, profilSchema } from "./schemas";

function Erreur({ erreur }: { erreur: unknown }) {
  if (!erreur) return null;
  return <Text couleur={colors.danger} accessibilityLiveRegion="polite">{isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}</Text>;
}

/**
 * Dernière étape de l'inscription : nom complet (demandé une seule fois), « Tu es » facultatif, mot de passe.
 * Les conditions ont été acceptées à l'étape 1, avant l'envoi du SMS : impossible d'arriver ici sans.
 */
export function InscriptionProfilScreen() {
  const flow = useAuthFlow();
  const inscription = useInscription();
  const [occupation, setOccupation] = useState<Occupation | null>(null);
  const { control, handleSubmit, formState: { errors } } = useForm<z.infer<typeof profilSchema>>({ resolver: zodResolver(profilSchema), defaultValues: { full_name: "", password: "" } });
  return (
    <Screen scroll>
      <EnTeteEtapes etape={2} total={2} />
      <View style={{ gap: sp[1] }}>
        <Text variante="titre">Présente-toi</Text>
        <Text muted>Ton nom apparaît aux gérants quand tu leur écris.</Text>
      </View>
      <Controller control={control} name="full_name" render={({ field }) => <TextField label={t.auth.nom} placeholder="Awa Bio" autoCapitalize="words" autoComplete="name" textContentType="name" value={field.value} onChangeText={field.onChange} erreur={errors.full_name?.message} aide="Ton prénom puis ton nom." />} />
      <ChoixOccupation valeur={occupation} onChange={setOccupation} />
      <Controller control={control} name="password" render={({ field }) => <PasswordField label={t.auth.motDePasse} value={field.value} onChangeText={field.onChange} erreur={errors.password?.message} aide="8 caractères au moins." />} />
      <Erreur erreur={inscription.error} />
      <Button titre={t.auth.creerCompte} chargement={inscription.isPending} onPress={handleSubmit((v) => flow.otpToken && inscription.mutate({ otpToken: flow.otpToken, full_name: v.full_name, password: v.password, occupation }, { onSuccess: flow.reinitialiser }))} />
    </Screen>
  );
}

/** Mot de passe oublié, dernière étape : nouveau mot de passe, puis retour à la connexion. */
export function MotDePasseNouveauScreen() {
  const router = useRouter();
  const flow = useAuthFlow();
  const reset = useReinitialiserMotDePasse();
  const { control, handleSubmit, formState: { errors } } = useForm<z.infer<typeof nouveauMotDePasseSchema>>({ resolver: zodResolver(nouveauMotDePasseSchema), defaultValues: { new_password: "" } });
  return (
    <Screen scroll>
      <Logotype />
      <Text variante="titre">Nouveau mot de passe</Text>
      <Controller control={control} name="new_password" render={({ field }) => <PasswordField label={t.auth.motDePasse} value={field.value} onChangeText={field.onChange} erreur={errors.new_password?.message} aide="8 caractères au moins." />} />
      <Erreur erreur={reset.error} />
      <Button titre={t.commun.enregistrer} chargement={reset.isPending} onPress={handleSubmit((v) => flow.otpToken && reset.mutate({ otpToken: flow.otpToken, new_password: v.new_password }, { onSuccess: () => { flow.reinitialiser(); router.replace("/connexion"); } }))} />
    </Screen>
  );
}
