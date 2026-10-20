import { Alert, View } from "react-native";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { sp, colors } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useAppareils, useRevoquerAppareil } from "./queries";

/** Écran Mes appareils : liste + révocation à distance (EF-CPT-06). */
export function AppareilsScreen() {
  const { c } = useTheme();
  const requete = useAppareils();
  const revoquer = useRevoquerAppareil();

  const confirmerRevocation = (id: string, label: string) => {
    Alert.alert(
      "Révoquer l'appareil",
      `Déconnecter « ${label} » ? Cet appareil devra se reconnecter.`,
      [
        { text: t.commun.annuler, style: "cancel" },
        {
          text: "Déconnecter",
          style: "destructive",
          onPress: () => void revoquer.mutate(id),
        },
      ],
    );
  };

  return (
    <Screen scroll>
      <Text variante="titre">Appareils connectés</Text>
      <Text muted>Retrouve ici tous les appareils qui ont accès à ton compte. Tu peux déconnecter ceux que tu ne reconnais pas.</Text>
      {revoquer.error ? (
        <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
          {isApiError(revoquer.error) ? messageErreur(revoquer.error.code, revoquer.error.message) : t.commun.erreurGenerique}
        </Text>
      ) : null}
      <QueryState query={requete}>
        {(appareils) =>
          appareils.length === 0 ? (
            <Text muted style={{ textAlign: "center", paddingVertical: sp[6] }}>Aucun appareil connecté.</Text>
          ) : (
            <View style={{ gap: sp[3] }}>
              {appareils.map((a) => (
                <View
                  key={a.id}
                  style={{
                    padding: sp[4],
                    borderRadius: 16,
                    borderWidth: 1,
                    borderColor: a.current ? c.primary : c.border,
                    backgroundColor: c.surface,
                    gap: sp[2],
                  }}
                >
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <View style={{ flex: 1, gap: 4 }}>
                      <Text variante="corpsGras">{a.label || "Appareil"}</Text>
                      <Text variante="legende" muted>
                        {a.platform === "ios" ? "iPhone / iPad" : "Android"} · Dernière activité {a.last_seen_at
                          ? new Date(a.last_seen_at).toLocaleDateString("fr-BJ", { day: "numeric", month: "short" })
                          : "inconnue"}
                      </Text>
                    </View>
                    {a.current ? (
                      <View
                        style={{
                          paddingHorizontal: sp[2],
                          paddingVertical: 2,
                          borderRadius: 999,
                          backgroundColor: c.primarySoft,
                        }}
                      >
                        <Text variante="legende" couleur={c.primary}>Cet appareil</Text>
                      </View>
                    ) : null}
                  </View>
                  {!a.current ? (
                    <Button
                      titre="Déconnecter"
                      variante="danger"
                      taille="compacte"
                      chargement={revoquer.isPending && revoquer.variables === a.id}
                      onPress={() => confirmerRevocation(a.id, a.label || "Appareil")}
                    />
                  ) : null}
                </View>
              ))}
            </View>
          )
        }
      </QueryState>
    </Screen>
  );
}
