import { CodeStep } from "@/features/auth/CodeStep";

export default function Page() {
  return <CodeStep objet="reset_password" suivant="/mot-de-passe/nouveau" />;
}
