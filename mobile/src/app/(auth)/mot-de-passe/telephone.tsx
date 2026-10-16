import { TelephoneStep } from "@/features/auth/TelephoneStep";

export default function Page() {
  return <TelephoneStep objet="reset_password" titre="Mot de passe oublié" consigne="Saisis le numéro de ton compte : tu recevras un code par SMS." suivant="/mot-de-passe/code" />;
}
