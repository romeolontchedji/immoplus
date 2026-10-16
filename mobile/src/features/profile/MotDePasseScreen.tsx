import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { motDePasse } from "@/features/auth/schemas";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { PasswordField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { useChangerMotDePasse } from "./queries";

const schema = z.object({
  old_password: z.string().min(1, "Obligatoire."),
  new_password: motDePasse,
  confirmer: z.string(),
}).refine((v) => v.new_password === v.confirmer, { message: "Les mots de passe ne correspondent pas.", path: ["confirmer"] });
type Valeurs = z.infer<typeof schema>;

/**
 * Changement de mot de passe depuis l'espace compte (EF-CPT-04).
 * L'ancien mot de passe est requis. Les autres appareils sont déconnectés côté serveur.
 */
export function MotDePasseScreen() {
  const changer = useChangerMotDePasse();
  const { control, handleSubmit, reset, formState: { errors, isSubmitSuccessful } } = useForm<Valeurs>({
    resolver: zodResolver(schema),
    defaultValues: { old_password: "", new_password: "", confirmer: "" },
  });
  const erreur = changer.error;
  const succes = isSubmitSuccessful && !changer.isPending && !erreur;

  return (
    <Screen scroll>
      <Text variante="titre">Changer le mot de passe</Text>
      <Text muted>Pour confirmer ton identité, saisis d'abord ton mot de passe actuel.</Text>
      <Controller
        control={control}
        name="old_password"
        render={({ field }) => (
          <PasswordField
            label="Mot de passe actuel"
            value={field.value}
            onChangeText={field.onChange}
            erreur={errors.old_password?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="new_password"
        render={({ field }) => (
          <PasswordField
            label="Nouveau mot de passe"
            value={field.value}
            onChangeText={field.onChange}
            erreur={errors.new_password?.message}
          />
        )}
      />
      <Controller
        control={control}
        name="confirmer"
        render={({ field }) => (
          <PasswordField
            label="Confirmer le mot de passe"
            value={field.value}
            onChangeText={field.onChange}
            erreur={errors.confirmer?.message}
          />
        )}
      />
      {erreur ? (
        <Text variante="legende" couleur="#D13B3B" accessibilityLiveRegion="polite">
          {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.commun.erreurGenerique}
        </Text>
      ) : null}
      {succes ? (
        <Text variante="legende" couleur="#12805C" accessibilityLiveRegion="polite">
          Mot de passe modifié. Les autres appareils ont été déconnectés.
        </Text>
      ) : null}
      <Button
        titre={t.commun.enregistrer}
        chargement={changer.isPending}
        onPress={handleSubmit((v) => {
          changer.reset();
          changer.mutate({ old_password: v.old_password, new_password: v.new_password }, {
            onSuccess: () => reset(),
          });
        })}
      />
    </Screen>
  );
}
