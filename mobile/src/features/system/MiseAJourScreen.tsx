import { Linking, Platform } from "react-native";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/** Écran plein cadre, sans issue : tant que l'application n'est pas à jour, rien d'autre n'est accessible (ENF-EVO-04). */
const MAGASIN = Platform.select({ ios: "itms-apps://apps.apple.com/app/immoplus", default: "market://details?id=bj.immoplus.app" });

export function MiseAJourScreen() {
  return (
    <Screen>
      <Logotype />
      <Text variante="titre">Mise à jour nécessaire</Text>
      <Text>{"Cette version de Immo+ n'est plus prise en charge. Mets l'application à jour pour continuer."}</Text>
      <Button titre="Mettre à jour" onPress={() => void Linking.openURL(MAGASIN)} />
    </Screen>
  );
}
