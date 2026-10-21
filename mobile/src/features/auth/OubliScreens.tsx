import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Linking, View } from "react-native";
import type { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { useContactEquipe } from "@/features/system/useAppConfig";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { PasswordField, TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { useCleDeSecours, useLienParEmail } from "./hooks";
import { cleSchema, lienEmailSchema } from "./schemas";

function Erreur({ erreur }: { erreur: unknown }) {
  if (!erreur) return null;
  return <Text couleur={colors.danger} accessibilityLiveRegion="polite">{isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}</Text>;
}

function Porte({ numero, titre, children }: { numero: number; titre: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: sp[2], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }}>
      <Text variante="corpsGras">{`${numero}. ${titre}`}</Text>
      {children}
    </View>
  );
}

/**
 * Mot de passe oublié, sans SMS (ADR 0009) : d'abord le lien par e-mail, puis la clé de secours, enfin l'équipe.
 */
export function OubliScreen() {
  const router = useRouter();
  const lien = useLienParEmail();
  const equipe = useContactEquipe();
  const { control, handleSubmit, formState: { errors } } = useForm<z.infer<typeof lienEmailSchema>>({
    resolver: zodResolver(lienEmailSchema), defaultValues: { identifier: "" },
  });
  return (
    <Screen scroll>
      <Text variante="titre">Mot de passe oublié</Text>
      <Text muted>Trois façons de retrouver ton compte, de la plus simple à la plus longue.</Text>

      <Porte numero={1} titre="Par e-mail">
        <Text variante="legende" muted>Si tu as ajouté et confirmé un e-mail, reçois un lien valable 30 minutes.</Text>
        {lien.isSuccess ? (
          <Text couleur={colors.successText} accessibilityLiveRegion="polite">
            Si ce compte a un e-mail confirmé, un lien vient d’y être envoyé. Ouvre-le sur ce téléphone.
          </Text>
        ) : (
          <>
            <Controller control={control} name="identifier" render={({ field }) => (
              <TextField label="Nom d’utilisateur ou e-mail" autoCapitalize="none" autoCorrect={false} value={field.value} onChangeText={field.onChange} erreur={errors.identifier?.message} />
            )} />
            <Erreur erreur={lien.error} />
            <Button titre="Recevoir un lien" chargement={lien.isPending} onPress={handleSubmit((v) => lien.mutate(v.identifier))} />
          </>
        )}
      </Porte>

      <Porte numero={2} titre="Avec ta clé de secours">
        <Text variante="legende" muted>La clé de 16 caractères donnée à la création de ton compte.</Text>
        <Button titre="J’ai ma clé de secours" variante="secondaire" onPress={() => router.push("/mot-de-passe/cle" as never)} />
      </Porte>

      <Porte numero={3} titre="Ni e-mail ni clé ?">
        <Text variante="legende" muted>
          Écris à l’équipe Immo+ : elle vérifiera que le compte est bien le tien, puis t’enverra un lien pour choisir un
          nouveau mot de passe.
        </Text>
        <Button titre="Écrire à l’équipe sur WhatsApp" variante="fantome" onPress={() => void Linking.openURL(equipe.whatsapp_url)} />
      </Porte>
    </Screen>
  );
}

/** Clé de secours : nouveau mot de passe ; une nouvelle clé s'affiche (l'ancienne ne sert qu'une fois). */
export function CleOubliScreen() {
  const router = useRouter();
  const cle = useCleDeSecours();
  const { control, handleSubmit, formState: { errors } } = useForm<z.input<typeof cleSchema>>({
    resolver: zodResolver(cleSchema), defaultValues: { username: "", recovery_key: "", new_password: "" },
  });
  return (
    <Screen scroll>
      <Text variante="titre">Avec ta clé de secours</Text>
      <Text muted>Ex. K7QM-2XPA-9RTD-H4WN. Une nouvelle clé te sera donnée juste après.</Text>
      <Controller control={control} name="username" render={({ field }) => (
        <TextField label="Nom d’utilisateur" autoCapitalize="none" autoCorrect={false} value={field.value} onChangeText={field.onChange} erreur={errors.username?.message} />
      )} />
      <Controller control={control} name="recovery_key" render={({ field }) => (
        <TextField label="Clé de secours" autoCapitalize="characters" autoCorrect={false} value={field.value} onChangeText={field.onChange} erreur={errors.recovery_key?.message} />
      )} />
      <Controller control={control} name="new_password" render={({ field }) => (
        <PasswordField label="Nouveau mot de passe" value={field.value} onChangeText={field.onChange} erreur={errors.new_password?.message} aide="10 caractères au moins." />
      )} />
      <Erreur erreur={cle.error} />
      <Button
        titre="Changer mon mot de passe"
        chargement={cle.isPending}
        onPress={handleSubmit((v) => {
          const d = cleSchema.parse(v);
          cle.mutate(d, { onSuccess: () => router.replace("/connexion") });
        })}
      />
    </Screen>
  );
}
