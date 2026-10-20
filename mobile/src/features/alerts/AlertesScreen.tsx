import { useMemo, useState } from "react";
import { Alert, Pressable, Switch, View } from "react-native";
import { useRouter } from "expo-router";
import { BellPlus, BellRing, ChevronDown, ChevronUp } from "lucide-react-native";
import { isApiError } from "@/api/errors";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { useDistricts, useTypesChambre } from "@/features/listings/queries";
import { messageErreur, t } from "@/i18n/fr";
import { proposerNotifications } from "@/features/notifications/DemandeNotifications";
import { useSession } from "@/state/session";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { EnTetePage } from "@/ui/components/EnTetePage";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { aUnCritere, CRITERES_VIDES, criteresDe, EditeurCriteres, resumeCriteres, versCorps, type Criteres } from "./EditeurCriteres";
import type { Alerte } from "./queries";
import { useAlertes, useCreerAlerte, useModifierAlerte, useSupprimerAlerte } from "./queries";

/**
 * Écran Alertes (EF-ALR-01 à EF-ALR-04) : les alertes actives seulement, un bouton « Créer une nouvelle alerte » en
 * haut qui seul fait apparaître les critères (demande du 2026-10-20), et les alertes en pause repliées en bas.
 */
export function AlertesScreen() {
  const { etat } = useSession();
  const router = useRouter();
  const districts = useDistricts();
  const requete = useAlertes(etat.statut === "connecte");
  const creer = useCreerAlerte();
  const supprimer = useSupprimerAlerte();
  const [criteres, setCriteres] = useState<Criteres>(CRITERES_VIDES);
  const [ouvert, setOuvert] = useState(false);
  const [vide, setVide] = useState(false);
  const [voirPause, setVoirPause] = useState(false);
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
      <EnTetePage titre="Mes alertes" sousTitre="Sois prévenu dès qu’une chambre correspond, avant qu’elle parte." />

      {ouvert ? (
        <View style={{ backgroundColor: colors.surface, borderRadius: rayon.cardL, padding: sp[4], gap: sp[4], ...ombre.card }}>
          <Text variante="sousTitre">Nouvelle alerte</Text>
          <EditeurCriteres
            valeur={criteres}
            onChange={(c) => {
              setCriteres(c);
              setVide(false);
            }}
          />
          {vide ? (
            <Text variante="corpsGras" couleur={colors.danger} accessibilityLiveRegion="polite">{t.erreurs.alert_empty}</Text>
          ) : null}
          {creer.error ? (
            <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
              {isApiError(creer.error) ? messageErreur(creer.error.code, creer.error.message) : t.erreurs.network}
            </Text>
          ) : null}
          <Button
            titre="Créer l'alerte"
            chargement={creer.isPending}
            onPress={() => {
              if (!aUnCritere(criteres)) return setVide(true);
              creer.mutate(versCorps(criteres), {
                onSuccess: () => {
                  setCriteres(CRITERES_VIDES);
                  setOuvert(false);
                  void proposerNotifications("alerte");
                },
              });
            }}
          />
          <Button titre={t.commun.annuler} variante="fantome" onPress={() => { setOuvert(false); setVide(false); setCriteres(CRITERES_VIDES); }} />
        </View>
      ) : (
        <Pressable
          accessibilityRole="button"
          onPress={() => setOuvert(true)}
          style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: sp[2], minHeight: 52, borderRadius: rayon.pilule, backgroundColor: pressed ? colors.blueHover : colors.primary })}
        >
          <BellPlus size={20} color={colors.white} />
          <Text variante="corpsGras" couleur={colors.white}>Créer une nouvelle alerte</Text>
        </Pressable>
      )}

      <QueryState query={requete} vide={{ quand: (data) => data.length === 0, titre: "Aucune alerte pour l'instant", texte: "Appuie sur « Créer une nouvelle alerte » pour commencer." }}>
        {(alertes) => {
          const actives = alertes.filter((a) => a.is_active);
          const enPause = alertes.filter((a) => !a.is_active);
          const carte = (alerte: Alerte) => (
            <AlerteCarte
              key={alerte.id}
              alerte={alerte}
              noms={noms}
              onModifier={() => router.push(`/modifier-alerte/${alerte.id}` as never)}
              onSupprimer={() => confirmerSuppression(alerte.id)}
              suppression={supprimer.isPending && supprimer.variables === alerte.id}
            />
          );
          return (
            <View style={{ gap: sp[3] }}>
              <Text variante="label" muted>Alertes actives ({actives.length})</Text>
              {actives.length ? actives.map(carte) : <Text muted>Aucune alerte active.</Text>}
              {enPause.length ? (
                <>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ expanded: voirPause }}
                    onPress={() => setVoirPause((v) => !v)}
                    style={{ flexDirection: "row", alignItems: "center", gap: sp[2], minHeight: 44, marginTop: sp[2] }}
                  >
                    <Text variante="label" muted>Alertes en pause ({enPause.length})</Text>
                    {voirPause ? <ChevronUp size={18} color={colors.textMuted} /> : <ChevronDown size={18} color={colors.textMuted} />}
                  </Pressable>
                  {voirPause ? enPause.map(carte) : null}
                </>
              ) : null}
            </View>
          );
        }}
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
