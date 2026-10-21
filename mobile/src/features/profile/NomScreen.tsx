import { colors } from "@/ui/theme/tokens";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { useState } from "react";
import { ChoixOccupation, type Occupation } from "@/features/auth/ChoixOccupation";
import { useModifierProfil } from "./queries";

const champNom = (libelle: string) => z.string().trim().min(1, `Indique ton ${libelle}.`).max(60, "60 caractères au plus.");
const schema = z.object({ first_name: champNom("prénom"), last_name: champNom("nom") });
type Valeurs = z.infer<typeof schema>;

/** Modifier prénom et nom affichés sur le profil (EF-CPT-03, ADR 0009) et « Tu es » (décision V2). */
export function NomScreen() {
  const { etat } = useSession();
  const modifier = useModifierProfil();
  const user = etat.statut === "connecte" ? etat.user : null;
  const [occupation, setOccupation] = useState<Occupation | null>(etat.statut === "connecte" ? (etat.user.occupation ?? null) : null);
  const { control, handleSubmit, formState: { errors, isSubmitSuccessful } } = useForm<Valeurs>({
    resolver: zodResolver(schema),
    defaultValues: { first_name: user?.first_name ?? "", last_name: user?.last_name ?? "" },
  });
  const erreur = modifier.error;

  return (
    <Screen scroll>
      <Text variante="titre">Mon profil</Text>
      <Text muted>Saisis ton prénom et ton nom tels qu’ils apparaîtront dans l’application.</Text>
      <Controller
        control={control}
        name="first_name"
        render={({ field }) => (
          <TextField label="Prénom" value={field.value} onChangeText={field.onChange} autoCapitalize="words" autoComplete="given-name" erreur={errors.first_name?.message} />
        )}
      />
      <Controller
        control={control}
        name="last_name"
        render={({ field }) => (
          <TextField label="Nom" value={field.value} onChangeText={field.onChange} autoCapitalize="words" autoComplete="family-name" erreur={errors.last_name?.message} />
        )}
      />
      <ChoixOccupation valeur={occupation} onChange={setOccupation} />
      {erreur ? (
        <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
          {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.commun.erreurGenerique}
        </Text>
      ) : null}
      {isSubmitSuccessful && !modifier.isPending && !erreur ? (
        <Text variante="legende" couleur={colors.success} accessibilityLiveRegion="polite">Profil mis à jour.</Text>
      ) : null}
      <Button
        titre={t.commun.enregistrer}
        chargement={modifier.isPending}
        onPress={handleSubmit((v) => void modifier.mutate({ first_name: v.first_name, last_name: v.last_name, occupation }))}
      />
    </Screen>
  );
}
