import { TelephoneStep } from "@/features/auth/TelephoneStep";

export default function Page() {
  return <TelephoneStep objet="signup" titre="Crée ton compte" consigne="Nous t'envoyons un code par SMS pour vérifier ton numéro." suivant="/inscription/code" />;
}
