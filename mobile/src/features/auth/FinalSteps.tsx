import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import type { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { PasswordField, TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { useAuthFlow } from "./flow";
import { useInscription, useReinitialiserMotDePasse } from "./hooks";
import { nouveauMotDePasseSchema, profilSchema } from "./schemas";

function Erreur({ erreur }: { erreur: unknown }) {
  if (!erreur) return null;
  return <Text couleur="#D13B3B" accessibilityLiveRegion="polite">{isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}</Text>;
}

/** Dernière étape de l'inscription : nom, mot de passe, conditions → compte créé et session ouverte. */
export function InscriptionProfilScreen() {
  const flow = useAuthFlow();
  const inscription = useInscription();
  const { control, handleSubmit, formState: { errors } } = useForm<z.infer<typeof profilSchema>>({ resolver: zodResolver(profilSchema), defaultValues: { full_name: "", password: "", terms_accepted: undefined as unknown as true } });
  return (
    <Screen scroll>
      <Text variante="titre">Crée ton compte</Text>
      <Controller control={control} name="full_name" render={({ field }) => <TextField label={t.auth.nom} autoComplete="name" textContentType="name" value={field.value} onChangeText={field.onChange} erreur={errors.full_name?.message} />} />
      <Controller control={control} name="password" render={({ field }) => <PasswordField label={t.auth.motDePasse} value={field.value} onChangeText={field.onChange} erreur={errors.password?.message} aide="8 caractères au moins." />} />
      <Controller control={control} name="terms_accepted" render={({ field }) => <SwitchRow titre={t.auth.cgu} valeur={field.value === true} onChange={(v) => field.onChange(v ? true : undefined)} />} />
      {errors.terms_accepted ? <Text variante="legende" couleur="#D13B3B">{errors.terms_accepted.message}</Text> : null}
      <Erreur erreur={inscription.error} />
      <Button titre={t.auth.creerCompte} chargement={inscription.isPending} onPress={handleSubmit((v) => flow.otpToken && inscription.mutate({ otpToken: flow.otpToken, full_name: v.full_name, password: v.password }, { onSuccess: flow.reinitialiser }))} />
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
      <Text variante="titre">Nouveau mot de passe</Text>
      <Controller control={control} name="new_password" render={({ field }) => <PasswordField label={t.auth.motDePasse} value={field.value} onChangeText={field.onChange} erreur={errors.new_password?.message} aide="8 caractères au moins." />} />
      <Erreur erreur={reset.error} />
      <Button titre={t.commun.enregistrer} chargement={reset.isPending} onPress={handleSubmit((v) => flow.otpToken && reset.mutate({ otpToken: flow.otpToken, new_password: v.new_password }, { onSuccess: () => { flow.reinitialiser(); router.replace("/connexion"); } }))} />
    </Screen>
  );
}
