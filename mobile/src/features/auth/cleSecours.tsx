import { useState, useSyncExternalStore } from "react";
import { Modal, Share, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { KeyRound } from "lucide-react-native";
import { Button } from "@/ui/components/Button";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { Text } from "@/ui/components/Text";
import { colors, rayon, sp } from "@/ui/theme/tokens";

/**
 * Clé de secours (ADR 0009) : donnée par le serveur une seule fois (inscription, clé utilisée ou régénérée).
 * Elle reste en mémoire le temps de l'afficher, jamais enregistrée sur le téléphone par l'application.
 */
type Origine = "inscription" | "renouvelee";
let enAttente: { cle: string; origine: Origine } | null = null;
const abonnes = new Set<() => void>();
const prevenir = () => abonnes.forEach((f) => f());

export function montrerCle(cle: string, origine: Origine) {
  enAttente = { cle, origine };
  prevenir();
}

function abonner(f: () => void) {
  abonnes.add(f);
  return () => abonnes.delete(f);
}

/** Affichée au-dessus de toute l'application tant que l'utilisateur n'a pas confirmé avoir gardé sa clé. */
export function CleSecoursHote() {
  const actuelle = useSyncExternalStore(abonner, () => enAttente);
  const [gardee, setGardee] = useState(false);
  if (!actuelle) return null;

  const fermer = () => {
    enAttente = null;
    setGardee(false);
    prevenir();
  };
  const garder = () =>
    void Share.share({
      message: `Ma clé de secours Immo+ : ${actuelle.cle}\nElle sert à choisir un nouveau mot de passe si je l'oublie. Ne pas la partager.`,
    });

  return (
    <Modal visible animationType="slide" onRequestClose={() => undefined}>
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg, padding: sp[5], gap: sp[4], justifyContent: "center" }}>
        <View style={{ alignItems: "center", gap: sp[3] }}>
          <View style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center" }}>
            <KeyRound size={30} color={colors.primary} />
          </View>
          <Text variante="titre" style={{ textAlign: "center" }}>
            {actuelle.origine === "inscription" ? "Ta clé de secours" : "Ta nouvelle clé de secours"}
          </Text>
          <Text muted style={{ textAlign: "center" }}>
            Elle te permet de choisir un nouveau mot de passe si tu l’oublies. Elle ne sera plus jamais affichée.
          </Text>
        </View>

        <View style={{ borderWidth: 2, borderStyle: "dashed", borderColor: colors.primary, borderRadius: rayon.card, backgroundColor: colors.blueSoft, padding: sp[5], alignItems: "center" }}>
          <Text selectable accessibilityLabel={`Clé de secours : ${actuelle.cle.split("").join(" ")}`} style={{ fontSize: 26, fontWeight: "800", letterSpacing: 2, color: colors.night }}>
            {actuelle.cle}
          </Text>
        </View>

        <View style={{ gap: sp[1] }}>
          <Text variante="legende" muted>• Fais une capture d’écran maintenant, ou écris-la sur papier.</Text>
          <Text variante="legende" muted>• Ne la donne à personne, même pas à l’équipe Immo+.</Text>
          <Text variante="legende" muted>• Ajoute aussi un e-mail dans ton profil : c’est le plus simple pour retrouver ton compte.</Text>
        </View>

        <Button titre="Garder la clé (notes, message à moi-même)" variante="secondaire" onPress={garder} />
        <SwitchRow titre="J’ai gardé ma clé de secours" valeur={gardee} onChange={setGardee} />
        <Button titre="Continuer" disabled={!gardee} onPress={fermer} />
      </SafeAreaView>
    </Modal>
  );
}
