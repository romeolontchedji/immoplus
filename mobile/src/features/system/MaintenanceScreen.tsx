import { useQueryClient } from "@tanstack/react-query";
import { qk } from "@/api/keys";
import { t } from "@/i18n/fr";
import { Button } from "@/ui/components/Button";
import { Logotype } from "@/ui/components/Logo";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

export function MaintenanceScreen({ message }: { message?: string }) {
  const qc = useQueryClient();
  return (
    <Screen>
      <Logotype />
      <Text variante="titre">Maintenance en cours</Text>
      <Text>{message ?? t.erreurs.maintenance}</Text>
      <Button titre={t.commun.reessayer} variante="secondaire" onPress={() => void qc.invalidateQueries({ queryKey: qk.appConfig })} />
    </Screen>
  );
}
