import { Linking, View } from "react-native";
import { activerPush } from "@/features/notifications/push";
import { sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { Text } from "@/ui/components/Text";
import { useEnregistrerPreferences, usePreferencesNotif } from "./queries";

/**
 * Préférences de notification (EF-NTF-02, EF-NTF-03).
 * Trois catégories : messages, alertes de chambre, rappels.
 * Si la permission est refusée, un bouton ouvre les réglages système.
 */
export function PreferencesNotificationsScreen() {
  const requete = usePreferencesNotif();
  const enregistrer = useEnregistrerPreferences();

  const basculer = (cle: "messages" | "alerts" | "reminders", valeur: boolean) => {
    if (!requete.data) return;
    const prochaines = { ...requete.data, [cle]: valeur };
    enregistrer.mutate(prochaines);
    // Mise à jour optimiste : si l'activation est demandée, activer le push
    if (valeur) void activerPush();
  };

  return (
    <Screen scroll>
      <Text variante="titre">Notifications</Text>
      <Text muted>Choisis les catégories pour lesquelles tu souhaites recevoir des notifications.</Text>
      <QueryState query={requete}>
        {(prefs) => (
          <View style={{ gap: sp[1] }}>
            <SwitchRow
              titre="Messages"
              aide="Nouveaux messages dans tes conversations"
              valeur={prefs.messages}
              onChange={(v) => basculer("messages", v)}
            />
            <SwitchRow
              titre="Alertes de chambre"
              aide="Nouvelles annonces correspondant à tes alertes"
              valeur={prefs.alerts}
              onChange={(v) => basculer("alerts", v)}
            />
            <SwitchRow
              titre="Rappels"
              aide="Activité à ne pas manquer sur tes favoris"
              valeur={prefs.reminders}
              onChange={(v) => basculer("reminders", v)}
            />
          </View>
        )}
      </QueryState>
      <Button
        titre="Ouvrir les réglages système"
        variante="secondaire"
        onPress={() => void Linking.openSettings()}
      />
    </Screen>
  );
}
