import { useState } from "react";
import { Alert, View } from "react-native";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useSupprimerCompte } from "./queries";

/**
 * Suppression définitive du compte (EF-CPT-07) : deux étapes de confirmation.
 * 1. L'utilisateur coche la case de confirmation.
 * 2. Il confirme dans une alerte native avant l'appel DELETE /v1/me.
 * La session est fermée et le cache vidé après la suppression (via useSupprimerCompte → fermer()).
 */
export function SupprimerCompteScreen() {
  const { c } = useTheme();
  const supprimer = useSupprimerCompte();
  const [confirme, setConfirme] = useState(false);

  const lancer = () => {
    Alert.alert(
      "Supprimer définitivement ?",
      "Toutes tes données (conversations, alertes, favoris) seront effacées. Cette action est irréversible.",
      [
        { text: t.commun.annuler, style: "cancel" },
        {
          text: "Supprimer",
          style: "destructive",
          onPress: () => void supprimer.mutate(),
        },
      ],
    );
  };

  return (
    <Screen scroll>
      <Text variante="titre">Supprimer mon compte</Text>

      {/* Avertissement */}
      <View
        style={{
          padding: sp[4],
          borderRadius: 12,
          backgroundColor: c.dangerBg,
          gap: sp[2],
        }}
      >
        <Text variante="corpsGras" couleur={c.danger}>Attention — action irréversible</Text>
        <Text muted couleur={c.dangerText}>
          La suppression de ton compte efface définitivement toutes tes données :
          conversations, alertes, favoris et historique. Tu ne pourras pas annuler cette action.
        </Text>
      </View>

      {/* Case de confirmation */}
      <Button
        titre={confirme ? "Je comprends les conséquences" : "Je comprends les conséquences"}
        variante={confirme ? "danger" : "secondaire"}
        onPress={() => setConfirme(!confirme)}
      />

      {supprimer.error ? (
        <Text variante="legende" couleur={c.danger} accessibilityLiveRegion="polite">
          {isApiError(supprimer.error) ? messageErreur(supprimer.error.code, supprimer.error.message) : t.commun.erreurGenerique}
        </Text>
      ) : null}

      <Button
        titre="Supprimer définitivement mon compte"
        variante="danger"
        chargement={supprimer.isPending}
        disabled={!confirme}
        onPress={lancer}
      />
    </Screen>
  );
}
