import { useSyncExternalStore } from "react";
import { Modal, Pressable, View } from "react-native";
import { BellRing, MessageCircle } from "lucide-react-native";
import { CLES_KV, kv } from "@/storage/kv";
import { Button } from "@/ui/components/Button";
import { Text } from "@/ui/components/Text";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { activerPush, etatAutorisation } from "./push";

/**
 * Explication avant la demande système (docs/plan-actions-v2.md §9.3). Android 13+ et iOS ne laissent demander qu'une
 * fois : un refus est presque définitif. On explique donc d'abord, au moment où la notification a un sens (premier
 * message envoyé, première alerte créée), et la demande système ne part que si la personne accepte.
 */
export type Contexte = "message" | "alerte";

const TEXTES: Record<Contexte, { titre: string; texte: string }> = {
  message: {
    titre: "Ne rate pas la réponse du gérant",
    texte: "Active les notifications : tu seras prévenu dès qu'il te répond, même application fermée.",
  },
  alerte: {
    titre: "Sois le premier sur la chambre",
    texte: "Active les notifications : on te prévient dès qu'une chambre correspond à ton alerte, avant les autres.",
  },
};

const DELAI_RELANCE_MS = 7 * 24 * 60 * 60 * 1000; // « Plus tard » : on ne redemande pas avant 7 jours

type Memoire = { reponse: "plus_tard"; le: number };

let ouvert: Contexte | null = null;
const abonnes = new Set<() => void>();
const changer = (c: Contexte | null) => {
  ouvert = c;
  abonnes.forEach((f) => f());
};

/** À appeler après une action qui rend les notifications utiles. Ne montre rien si c'est inutile ou trop tôt. */
export async function proposerNotifications(contexte: Contexte): Promise<void> {
  const etat = await etatAutorisation();
  if (etat === "accordee") {
    await activerPush().catch(() => undefined); // déjà accordée : on enregistre simplement le jeton
    return;
  }
  if (etat !== "a_demander") return; // indisponible (Expo Go, émulateur) ou refus définitif
  const memoire = await kv.get<Memoire>(CLES_KV.demandeNotifications);
  if (memoire && Date.now() - memoire.le < DELAI_RELANCE_MS) return;
  changer(contexte);
}

/** Monté une fois à la racine : affiche la feuille quand `proposerNotifications` l'ouvre. */
export function DemandeNotificationsHote() {
  const contexte = useSyncExternalStore(
    (f) => (abonnes.add(f), () => void abonnes.delete(f)),
    () => ouvert,
  );
  if (!contexte) return null;
  const { titre, texte } = TEXTES[contexte];
  const plusTard = () => {
    void kv.set(CLES_KV.demandeNotifications, { reponse: "plus_tard", le: Date.now() } satisfies Memoire);
    changer(null);
  };
  const Icone = contexte === "message" ? MessageCircle : BellRing;

  return (
    <Modal transparent animationType="slide" visible onRequestClose={plusTard} statusBarTranslucent>
      <Pressable accessibilityLabel="Fermer" onPress={plusTard} style={{ flex: 1, backgroundColor: "rgba(15, 27, 61, 0.45)" }} />
      <View style={{ backgroundColor: colors.surface, borderTopLeftRadius: rayon.sheet, borderTopRightRadius: rayon.sheet, padding: sp[6], paddingBottom: sp[10], gap: sp[4], ...ombre.pop }}>
        <View style={{ alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: colors.border }} />
        <View style={{ width: 64, height: 64, borderRadius: 20, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center", alignSelf: "center" }}>
          <Icone size={30} color={colors.primary} />
        </View>
        <View style={{ gap: sp[2] }}>
          <Text variante="titreSection" style={{ textAlign: "center" }}>{titre}</Text>
          <Text muted style={{ textAlign: "center", lineHeight: 22 }}>{texte}</Text>
          <Text variante="legende" muted style={{ textAlign: "center" }}>Tu pourras changer d’avis à tout moment dans ton profil.</Text>
        </View>
        <Button
          titre="Activer les notifications"
          onPress={() => {
            changer(null);
            void activerPush().catch(() => undefined); // ouvre la demande du système
          }}
        />
        <Button titre="Plus tard" variante="fantome" onPress={plusTard} />
      </View>
    </Modal>
  );
}
