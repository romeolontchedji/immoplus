import { useCallback, useEffect, useState } from "react";
import { AppState, Linking, View } from "react-native";
import { BellOff, BellRing } from "lucide-react-native";
import { activerPush, etatAutorisation } from "@/features/notifications/push";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { Text } from "@/ui/components/Text";
import { useEnregistrerPreferences, usePreferencesNotif, type PreferencesNotif } from "./queries";

type Etat = Awaited<ReturnType<typeof etatAutorisation>>;

/** Bandeau sur l'autorisation du téléphone : sans elle, les réglages ci-dessous n'ont aucun effet. */
function EtatTelephone({ etat, onActiver }: { etat: Etat | null; onActiver: () => void }) {
  if (!etat || etat === "accordee") return null;
  const contenu = {
    a_demander: { texte: "Les notifications sont coupées sur ce téléphone. Active-les pour être prévenu des réponses et des nouvelles chambres.", action: "Activer les notifications", agir: onActiver },
    refusee: { texte: "Tu as refusé les notifications pour Immo+. Réactive-les dans les réglages du téléphone.", action: "Ouvrir les réglages", agir: () => void Linking.openSettings() },
    indisponible: { texte: "Les notifications push ne fonctionnent pas dans Expo Go ni sur émulateur : il faut l'application installée.", action: null, agir: null },
  }[etat];
  return (
    <View style={{ gap: sp[3], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.warningBg }}>
      <View style={{ flexDirection: "row", gap: sp[3] }}>
        <BellOff size={20} color={colors.warningText} />
        <Text variante="legende" couleur={colors.warningText} style={{ flex: 1, lineHeight: 19 }}>{contenu.texte}</Text>
      </View>
      {contenu.action && contenu.agir ? <Button titre={contenu.action} taille="compacte" onPress={contenu.agir} /> : null}
    </View>
  );
}

/**
 * Préférences de notification (EF-NTF-02, EF-NTF-03) : messages (avec ou sans aperçu du texte), alertes de chambre,
 * rappels. Les notifications de sécurité et de sanction ne se coupent pas (règle serveur).
 */
export function PreferencesNotificationsScreen() {
  const requete = usePreferencesNotif();
  const enregistrer = useEnregistrerPreferences();
  const [etat, setEtat] = useState<Etat | null>(null);

  const relire = useCallback(() => void etatAutorisation().then(setEtat), []);
  useEffect(() => {
    relire();
    const abonnement = AppState.addEventListener("change", (s) => s === "active" && relire()); // retour des réglages
    return () => abonnement.remove();
  }, [relire]);

  const basculer = (prefs: PreferencesNotif, cle: keyof PreferencesNotif, valeur: boolean) => {
    enregistrer.mutate({ ...prefs, [cle]: valeur });
    if (valeur && etat === "a_demander") void activerPush().then(relire);
  };

  return (
    <Screen scroll>
      <View style={{ flexDirection: "row", alignItems: "center", gap: sp[3] }}>
        <View style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center" }}>
          <BellRing size={22} color={colors.primary} />
        </View>
        <Text variante="titre">Notifications</Text>
      </View>
      <Text muted>Choisis ce qui te prévient sur ce téléphone. Tout reste visible dans le centre de notifications.</Text>

      <EtatTelephone etat={etat} onActiver={() => void activerPush().then(relire)} />

      <QueryState query={requete}>
        {(prefs) => (
          <View style={{ backgroundColor: colors.surface, borderRadius: rayon.card, borderWidth: 1, borderColor: colors.border, paddingHorizontal: sp[4], paddingVertical: sp[2] }}>
            <SwitchRow titre="Messages" aide="Réponses dans tes conversations" valeur={prefs.messages} onChange={(v) => basculer(prefs, "messages", v)} />
            {prefs.messages ? (
              <SwitchRow titre="Aperçu du message" aide="Afficher le texte dans la notification (sinon « Nouveau message »)" valeur={prefs.apercu} onChange={(v) => basculer(prefs, "apercu", v)} />
            ) : null}
            <SwitchRow titre="Alertes de chambre" aide="Nouvelles chambres qui correspondent à tes alertes" valeur={prefs.alertes} onChange={(v) => basculer(prefs, "alertes", v)} />
            <SwitchRow titre="Rappels" aide="Chambres à confirmer, messages en attente de réponse" valeur={prefs.rappels} onChange={(v) => basculer(prefs, "rappels", v)} />
          </View>
        )}
      </QueryState>
      {enregistrer.isError ? <Text variante="legende" couleur={colors.danger}>Enregistrement impossible. Vérifie ta connexion et réessaie.</Text> : null}
      <Text variante="legende" muted>Les notifications de sécurité du compte ne peuvent pas être coupées.</Text>
    </Screen>
  );
}
