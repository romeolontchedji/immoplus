import { Link } from "expo-router";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

export default function NotFound() {
  return (
    <Screen>
      <Text variante="titre">Page introuvable</Text>
      <Link href="/"><Text variante="lien">{"Retour à l'accueil"}</Text></Link>
    </Screen>
  );
}
