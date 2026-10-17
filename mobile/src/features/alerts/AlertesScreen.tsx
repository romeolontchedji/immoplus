import { useMemo, useState } from "react";
import { Alert, Switch, View } from "react-native";
import { useRouter } from "expo-router";
import { BellRing } from "lucide-react-native";
import { isApiError } from "@/api/errors";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { useDistricts, useTypesChambre } from "@/features/listings/queries";
import { messageErreur, t } from "@/i18n/fr";
import { proposerNotifications } from "@/features/notifications/DemandeNotifications";
import { useSession } from "@/state/session";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { CRITERES_VIDES, criteresDe, EditeurCriteres, resumeCriteres, versCorps, type Criteres } from "./EditeurCriteres";
import type { Alerte } from "./queries";
import { useAlertes, useCreerAlerte, useModifierAlerte, useSupprimerAlerte } from "./queries";

/**
 * Écran Alertes (EF-ALR-01 à EF-ALR-04, maquette Mobile · Alertes) : formulaire « Nouvelle alerte » dans une carte,
 * puis les alertes avec interrupteur actif / en pause, modification et suppression confirmée.
 */
export function AlertesScreen() {
  const { etat } = useSession();
  const router = useRouter();
  const districts = useDistricts();
  const requete = useAlertes(etat.statut === "connecte");
  const creer = useCreerAlerte();
  const supprimer = useSupprimerAlerte();
  const [criteres, setCriteres] = useState<Criteres>(CRITERES_VIDES);
  const noms = useMemo(() => Object.fromEntries((districts.data ?? []).map((d) => [d.id, d.name])), [districts.data]);

  if (etat.statut !== "connecte") {
    return (
      <Screen scroll>
        <AuthRequired />
      </Screen>
    );
  }

  const confirmerSuppression = (id: string) => {
    Alert.alert("Supprimer l'alerte ?", "Tu ne recevras plus de notifications pour ces critères.", [
      { text: t.commun.annuler, style: "cancel" },
      { text: "Supprimer", style: "destructive", onPress: () => void supprimer.mutate(id) },
    ]);
  };

  return (
    <Screen scroll>
      <View style={{ gap: sp[1] }}>
        <Text variante="titre">Mes alertes</Text>
        <Text muted>Sois prévenu dès qu’une chambre correspond, avant qu’elle parte.</Text>
      </View>

      <View style={{ backgroundColor: colors.surface, borderRadius: rayon.cardL, padding: sp[4], gap: sp[4], ...ombre.card }}>
        <Text variante="sousTitre">Nouvelle alerte</Text>
        <EditeurCriteres valeur={criteres} onChange={setCriteres} />
        {creer.error ? (
          <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
            {isApiError(creer.error) ? messageErreur(creer.error.code, creer.error.message) : t.erreurs.network}
          </Text>
        ) : null}
        <Button titre="Créer l'alerte" chargement={creer.isPending} onPress={() => creer.mutate(versCorps(criteres), { onSuccess: () => { setCriteres(CRITERES_VIDES); void proposerNotifications("alerte"); } })} />
      </View>

      <QueryState query={requete} vide={{ quand: (data) => data.length === 0, titre: "Aucune alerte pour l'instant", texte: "Crée ta première alerte ci-dessus." }}>
        {(alertes) => (
          <View style={{ gap: sp[3] }}>
            <Text variante="label" muted>Mes alertes ({alertes.length})</Text>
            {alertes.map((alerte) => (
              <AlerteCarte
                key={alerte.id}
                alerte={alerte}
                noms={noms}
                onModifier={() => router.push(`/modifier-alerte/${alerte.id}` as never)}
                onSupprimer={() => confirmerSuppression(alerte.id)}
                suppression={supprimer.isPending && supprimer.variables === alerte.id}
              />
            ))}
          </View>
        )}
      </QueryState>
    </Screen>
  );
}

function AlerteCarte({ alerte, noms, onModifier, onSupprimer, suppression }: {
  alerte: Alerte;
  noms: Record<string, string>;
  onModifier: () => void;
  onSupprimer: () => void;
  suppression: boolean;
}) {
  const modifier = useModifierAlerte(alerte.id);
  const types = useTypesChambre();
  const { titre, details } = resumeCriteres(criteresDe(alerte), noms, types);
  const actif = modifier.isPending && modifier.variables?.is_active !== undefined ? !!modifier.variables.is_active : alerte.is_active;

  return (
    <View style={{ backgroundColor: colors.surface, borderRadius: rayon.card, padding: sp[4], gap: sp[3], borderWidth: 1, borderColor: colors.border, opacity: actif ? 1 : 0.75 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: sp[3] }}>
        <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: actif ? colors.blueSoft : colors.divider, alignItems: "center", justifyContent: "center" }}>
          <BellRing size={20} color={actif ? colors.primary : colors.textMuted} />
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Text variante="corpsGras" numberOfLines={2}>{alerte.label || titre}</Text>
          {details ? <Text variante="legende" muted>{details}</Text> : null}
          <Text variante="legende" couleur={actif ? colors.successText : colors.textMuted} style={{ fontWeight: "700" }}>{actif ? "Active" : "En pause"}</Text>
        </View>
        <Switch
          accessibilityLabel={actif ? "Mettre l'alerte en pause" : "Réactiver l'alerte"}
          value={actif}
          onValueChange={(v) => modifier.mutate({ is_active: v })}
          trackColor={{ true: colors.success, false: colors.border }}
        />
      </View>
      <View style={{ flexDirection: "row", gap: sp[2] }}>
        <Button titre="Modifier" variante="secondaire" taille="compacte" style={{ flex: 1 }} onPress={onModifier} />
        <Button titre="Supprimer" variante="fantome" taille="compacte" style={{ flex: 1 }} chargement={suppression} onPress={onSupprimer} />
      </View>
    </View>
  );
}
