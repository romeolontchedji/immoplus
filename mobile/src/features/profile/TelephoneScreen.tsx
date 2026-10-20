import { colors } from "@/ui/theme/tokens";
import { Vibration } from "react-native";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { isApiError } from "@/api/errors";
import { useDemanderCode, useVerifierCode } from "@/features/auth/hooks";
import { codeSchema, telephone } from "@/features/auth/schemas";
import { versE164 } from "@/lib/phone";
import { messageErreur, t } from "@/i18n/fr";
import { Button } from "@/ui/components/Button";
import { PasswordField, PhoneField, TextField } from "@/ui/components/TextField";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useChangerTelephone } from "./queries";

type Etape = "telephone" | "code";

const telephoneSchema = z.object({ phone: telephone });
type ValeursPhone = z.infer<typeof telephoneSchema>;
const codeSchemaAvecMdp = codeSchema.extend({
  password: z.string().min(1, "Mot de passe requis."),
});
type ValeursCode = z.infer<typeof codeSchemaAvecMdp>;

/**
 * Changement de numéro en deux temps (EF-CPT-05) :
 * 1. Saisie du nouveau numéro → OTP envoyé.
 * 2. Code OTP → finalisation avec POST /v1/me/phone/change.
 */
export function TelephoneScreen() {
  const [etape, setEtape] = useState<Etape>("telephone");
  const [phone, setPhone] = useState("");
  const [otpToken, setOtpToken] = useState("");

  const demanderCode = useDemanderCode("change_phone");
  const verifierCode = useVerifierCode("change_phone");
  const changer = useChangerTelephone();

  const formePhone = useForm<ValeursPhone>({
    resolver: zodResolver(telephoneSchema),
    defaultValues: { phone: "" },
  });
  const formeCode = useForm<ValeursCode>({
    resolver: zodResolver(codeSchemaAvecMdp),
    defaultValues: { code: "", password: "" },
  });

  if (etape === "telephone") {
    const erreur = demanderCode.error;
    return (
      <Screen scroll>
        <Text variante="titre">Changer de numéro</Text>
        <Text muted>Saisis ton nouveau numéro béninois. Tu recevras un code SMS pour confirmer le changement.</Text>
        <Controller
          control={formePhone.control}
          name="phone"
          render={({ field }) => (
            <PhoneField
              value={field.value}
              onChangeText={field.onChange}
              erreur={formePhone.formState.errors.phone?.message}
            />
          )}
        />
        {erreur ? (
          <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
            {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.commun.erreurGenerique}
          </Text>
        ) : null}
        <Button
          titre="Recevoir le code"
          chargement={demanderCode.isPending}
          onPress={formePhone.handleSubmit((v) => {
            const e164 = versE164(v.phone)!;
            demanderCode.mutate(v.phone, {
              onSuccess: () => { setPhone(e164); setEtape("code"); },
            });
          })}
        />
      </Screen>
    );
  }

  const erreur = verifierCode.error ?? changer.error;
  return (
    <Screen scroll>
      <Text variante="titre">Code de confirmation</Text>
      <Text muted>Un code à 6 chiffres a été envoyé au {phone}.</Text>
      <Controller
        control={formeCode.control}
        name="code"
        render={({ field }) => (
          <TextField
            label="Code reçu par SMS"
            value={field.value}
            onChangeText={field.onChange}
            keyboardType="number-pad"
            maxLength={6}
            autoComplete="sms-otp"
            textContentType="oneTimeCode"
            erreur={formeCode.formState.errors.code?.message}
          />
        )}
      />
      <Controller
        control={formeCode.control}
        name="password"
        render={({ field }) => (
          <PasswordField
            label="Mot de passe actuel"
            value={field.value}
            onChangeText={field.onChange}
            erreur={formeCode.formState.errors.password?.message}
          />
        )}
      />
      {erreur ? (
        <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
          {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.commun.erreurGenerique}
        </Text>
      ) : null}
      {changer.isSuccess ? (
        <Text variante="legende" couleur={colors.success} accessibilityLiveRegion="polite">Numéro mis à jour.</Text>
      ) : null}
      <Button
        titre="Confirmer"
        chargement={verifierCode.isPending || changer.isPending}
        onPress={formeCode.handleSubmit((v) => {
          verifierCode.mutate({ phone, code: v.code }, {
            onSuccess: (token) => {
              formeCode.setValue("code", "");
              setOtpToken(token);
              changer.mutate({ otp_token: token, password: v.password });
            },
            onError: () => {
              Vibration.vibrate([0, 60, 80, 60]); // code refusé : on vide la case pour le prochain essai
              formeCode.setValue("code", "");
            },
          });
        })}
      />
    </Screen>
  );
}
