import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { View } from "react-native";
import { z } from "zod";
import { isApiError } from "@/api/errors";
import { montrerCle } from "@/features/auth/cleSecours";
import { messageErreur, t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { PasswordField, TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { useAjouterEmail, useNouvelleCle } from "./queries";

function Erreur({ erreur }: { erreur: unknown }) {
  if (!erreur) return null;
  return <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">{isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}</Text>;
}

function Bloc({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: sp[2], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }}>
      <Text variante="corpsGras">{titre}</Text>
      {children}
    </View>
  );
}

/**
 * « Retrouver mon compte » (ADR 0009) : l'e-mail d'abord (lien de réinitialisation), puis la clé de secours.
 * Sans l'un ni l'autre, seule l'équipe peut aider : cet écran pousse à les tenir à jour.
 */
export function SecuriteScreen() {
  const { etat } = useSession();
  const user = etat.statut === "connecte" ? etat.user : null;
  const email = useAjouterEmail();
  const cle = useNouvelleCle();
  const formEmail = useForm<{ email: string }>({ resolver: zodResolver(z.object({ email: z.string().trim().email("Adresse e-mail invalide.") })), defaultValues: { email: "" } });
  const formCle = useForm<{ password: string }>({ resolver: zodResolver(z.object({ password: z.string().min(1, "Obligatoire.") })), defaultValues: { password: "" } });

  return (
    <Screen scroll>
      <Text variante="titre">Retrouver mon compte</Text>
      <Text muted>Si tu oublies ton mot de passe : un lien par e-mail d’abord, sinon ta clé de secours.</Text>

      <Bloc titre="Adresse e-mail">
        <Text variante="legende" muted>
          {user?.email ? `Confirmée : ${user.email}. Tu peux la remplacer.` : "Aucune adresse confirmée : ajoute-en une, c’est le plus simple."}
        </Text>
        {email.isSuccess ? (
          <Text variante="legende" couleur={colors.successText} accessibilityLiveRegion="polite">
            Lien de confirmation envoyé (valable 24 heures). Ouvre-le pour terminer.
          </Text>
        ) : (
          <>
            <Controller control={formEmail.control} name="email" render={({ field }) => (
              <TextField label="Adresse e-mail" keyboardType="email-address" autoCapitalize="none" autoComplete="email" value={field.value} onChangeText={field.onChange} erreur={formEmail.formState.errors.email?.message} />
            )} />
            <Erreur erreur={email.error} />
            <Button titre="Envoyer un lien de confirmation" variante="secondaire" chargement={email.isPending} onPress={formEmail.handleSubmit((v) => email.mutate(v.email))} />
          </>
        )}
      </Bloc>

      <Bloc titre="Clé de secours">
        <Text variante="legende" muted>
          {user?.recovery_key_created_at
            ? `Créée le ${new Date(user.recovery_key_created_at).toLocaleDateString("fr-FR")}. Perdue ? Crées-en une nouvelle : l’ancienne ne vaudra plus rien.`
            : "Tu n’as pas encore de clé de secours : crées-en une."}
        </Text>
        <Controller control={formCle.control} name="password" render={({ field }) => (
          <PasswordField label="Ton mot de passe actuel" value={field.value} onChangeText={field.onChange} erreur={formCle.formState.errors.password?.message} />
        )} />
        <Erreur erreur={cle.error} />
        <Button
          titre="Créer une nouvelle clé"
          variante="secondaire"
          chargement={cle.isPending}
          onPress={formCle.handleSubmit((v) => cle.mutate(v.password, { onSuccess: (nouvelle) => { formCle.reset(); montrerCle(nouvelle, "renouvelee"); } }))}
        />
      </Bloc>
    </Screen>
  );
}
