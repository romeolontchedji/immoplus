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

const schema = z.object({ full_name: z.string().trim().min(2, "Au moins 2 caractères.").max(80, "80 caractères au plus.") });
type Valeurs = z.infer<typeof schema>;

/** Modifier le nom complet affiché sur le profil (EF-CPT-03) et « Tu es » (décision V2). */
export function NomScreen() {
  const { etat } = useSession();
  const modifier = useModifierProfil();
  const nom = etat.statut === "connecte" ? etat.user.full_name : "";
  const [occupation, setOccupation] = useState<Occupation | null>(etat.statut === "connecte" ? (etat.user.occupation ?? null) : null);
  const { control, handleSubmit, formState: { errors, isSubmitSuccessful } } = useForm<Valeurs>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: nom },
  });
  const erreur = modifier.error;

  return (
    <Screen scroll>
      <Text variante="titre">Mon profil</Text>
      <Text muted>Saisis ton prénom et ton nom tels qu’ils apparaîtront dans l’application.</Text>
      <Controller
        control={control}
        name="full_name"
        render={({ field }) => (
          <TextField
            label="Nom complet"
            value={field.value}
            onChangeText={field.onChange}
            autoCapitalize="words"
            autoComplete="name"
            erreur={errors.full_name?.message}
          />
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
        onPress={handleSubmit((v) => void modifier.mutate({ full_name: v.full_name, occupation }))}
      />
    </Screen>
  );
}
