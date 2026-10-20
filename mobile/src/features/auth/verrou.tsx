import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { AppState, StyleSheet, View } from "react-native";
import * as LocalAuthentication from "expo-local-authentication";
import { Fingerprint } from "lucide-react-native";
import { useSession } from "@/state/session";
import { CLES_KV, kv } from "@/storage/kv";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Text } from "@/ui/components/Text";
import { colors, sp } from "@/ui/theme/tokens";

/**
 * Verrou biométrique facultatif (ADR 0005) : protège l'application ouverte, la session serveur reste inchangée.
 * Réglage local à l'appareil ; aucune donnée biométrique n'est lue par l'application (le système répond oui ou non).
 */
const DELAI_ARRIERE_PLAN_MS = 5 * 60 * 1000;

type Etat = { charge: boolean; actif: boolean; verrouille: boolean };
let etat: Etat = { charge: false, actif: false, verrouille: false };
const abonnes = new Set<() => void>();
const modifier = (m: Partial<Etat>) => {
  etat = { ...etat, ...m };
  abonnes.forEach((f) => f());
};
const abonner = (f: () => void) => (abonnes.add(f), () => void abonnes.delete(f));
// Démarrage à froid : verrouillé d'emblée si le réglage est actif (l'écran n'apparaît que si la session est ouverte).
void kv.get<boolean>(CLES_KV.verrouBiometrique).then((v) => modifier({ charge: true, actif: v === true, verrouille: v === true }));

/** Capteur présent et au moins une empreinte (ou un visage) enregistrée sur le téléphone. */
export async function biometrieDisponible(): Promise<boolean> {
  try {
    return (await LocalAuthentication.hasHardwareAsync()) && (await LocalAuthentication.isEnrolledAsync());
  } catch {
    return false; // module absent (Expo Go ancien, web) : le réglage n'est pas proposé
  }
}

async function authentifier(message: string): Promise<boolean> {
  try {
    const r = await LocalAuthentication.authenticateAsync({ promptMessage: message, cancelLabel: "Annuler", disableDeviceFallback: false });
    return r.success;
  } catch {
    return false;
  }
}

/** Pour l'écran de réglage : état, disponibilité, activation (après une réussite) et désactivation. */
export function useVerrouBiometrique() {
  const actif = useSyncExternalStore(abonner, () => etat.actif);
  const [disponible, setDisponible] = useState<boolean | null>(null);
  useEffect(() => void biometrieDisponible().then(setDisponible), []);
  return {
    actif,
    disponible,
    async activer(): Promise<boolean> {
      if (!(await authentifier("Confirme ton empreinte pour activer le verrou"))) return false;
      await kv.set(CLES_KV.verrouBiometrique, true);
      modifier({ actif: true });
      return true;
    },
    async desactiver(): Promise<void> {
      await kv.remove(CLES_KV.verrouBiometrique);
      modifier({ actif: false, verrouille: false });
    },
  };
}

async function deverrouiller(): Promise<void> {
  if (await authentifier("Déverrouille Immo+")) modifier({ verrouille: false });
}

/** Monté une fois à la racine : verrouille au démarrage et après 5 minutes en arrière-plan. */
export function VerrouHote() {
  const { etat: session, fermer } = useSession();
  const { charge, verrouille } = useSyncExternalStore(abonner, () => etat);
  const connecte = session.statut === "connecte";
  const affiche = charge && verrouille && connecte;
  const misEnArrierePlan = useRef<number | null>(null);

  // Déconnexion (volontaire ou forcée) : le réglage est effacé avec la session.
  useEffect(() => {
    if (session.statut !== "deconnecte" || !etat.actif) return;
    void kv.remove(CLES_KV.verrouBiometrique);
    modifier({ actif: false, verrouille: false });
  }, [session.statut]);

  useEffect(() => {
    const abonnement = AppState.addEventListener("change", (s) => {
      if (s === "background") misEnArrierePlan.current = Date.now();
      if (s === "active" && misEnArrierePlan.current !== null) {
        const absent = Date.now() - misEnArrierePlan.current;
        misEnArrierePlan.current = null;
        if (etat.actif && absent >= DELAI_ARRIERE_PLAN_MS) modifier({ verrouille: true });
      }
    });
    return () => abonnement.remove();
  }, []);

  useEffect(() => {
    if (affiche) void deverrouiller(); // propose la biométrie dès l'affichage
  }, [affiche]);

  if (!affiche) return null;
  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", padding: sp[8], gap: sp[5] }]} accessibilityViewIsModal>
      <Logotype taille={36} />
      <View style={{ width: 72, height: 72, borderRadius: 24, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center" }}>
        <Fingerprint size={36} color={colors.primary} />
      </View>
      <View style={{ gap: sp[2], alignItems: "center" }}>
        <Text variante="titreSection">Immo+ est verrouillé</Text>
        <Text muted style={{ textAlign: "center" }}>Utilise ton empreinte ou le code de ton téléphone pour continuer.</Text>
      </View>
      <Button titre="Déverrouiller" onPress={() => void deverrouiller()} style={{ alignSelf: "stretch" }} />
      <Button titre="Se déconnecter" variante="fantome" onPress={() => void fermer()} style={{ alignSelf: "stretch" }} />
    </View>
  );
}
