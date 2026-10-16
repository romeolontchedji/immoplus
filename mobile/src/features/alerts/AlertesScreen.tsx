import { Alert, Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { CIBLE_MIN, colors, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { useDistricts } from "@/features/listings/queries";
import type { Alerte, AlerteEntree } from "./queries";
import { useAlertes, useCreerAlerte, useModifierAlerte, useSupprimerAlerte } from "./queries";

const TYPES = ["single", "entree_coucher", "chambre_salon", "studio"] as const;
type TypeChambre = typeof TYPES[number];

type FormValeurs = {
  district: string[];
  rent_max: string;
  type: TypeChambre[];
};

/**
 * Écran Alertes (EF-ALR-01 à EF-ALR-04).
 * Conforme à la maquette « Mobile · Alertes@1x.png » :
 * - Formulaire « Nouvelle alerte » inline dans une carte blanche
 * - Chips quartier + type bleu cobalt quand actif
 * - Section "ALERTES ACTIVES" en dessous avec toggle vert
 */
export function AlertesScreen() {
  const { etat } = useSession();
  const { c } = useTheme();
  const router = useRouter();
  const districts = useDistricts();
  const requete = useAlertes(etat.statut === "connecte");
  const creer = useCreerAlerte();
  const supprimer = useSupprimerAlerte();

  const { control, handleSubmit, watch, setValue, reset } = useForm<FormValeurs>({
    defaultValues: { district: [], rent_max: "", type: [] },
  });
  const districtsSel = watch("district");
  const typesSel = watch("type");

  const basculerDistrict = (slug: string) =>
    setValue("district", districtsSel.includes(slug)
      ? districtsSel.filter((d) => d !== slug)
      : [...districtsSel, slug]);

  const basculerType = (tp: TypeChambre) =>
    setValue("type", typesSel.includes(tp)
      ? typesSel.filter((tt) => tt !== tp)
      : [...typesSel, tp]);

  const soumettre = (v: FormValeurs) => {
    const corps: AlerteEntree = {
      rent_max: v.rent_max ? Number(v.rent_max.replace(/\s/g, "")) : undefined,
      district: v.district.length ? v.district : undefined,
      type: v.type.length ? v.type : undefined,
    };
    creer.mutate(corps, { onSuccess: () => reset() });
  };

  const confirmerSuppression = (id: string) => {
    Alert.alert("Supprimer l'alerte ?", "Tu ne recevras plus de notifications pour ces critères.", [
      { text: t.commun.annuler, style: "cancel" },
      { text: "Supprimer", style: "destructive", onPress: () => void supprimer.mutate(id) },
    ]);
  };

  if (etat.statut !== "connecte") {
    return (
      <Screen scroll>
        <AuthRequired />
      </Screen>
    );
  }

  return (
    <Screen scroll>
      {/* En-tête */}
      <Text variante="titre">Mes alertes</Text>
      <Text muted style={{ marginBottom: sp[4] }}>
        Sois prévenu dès qu'une chambre correspond, avant qu'elle parte.
      </Text>

      {/* ── Formulaire Nouvelle alerte dans une carte blanche (conforme maquette) ── */}
      <View
        style={{
          backgroundColor: c.surface,
          borderRadius: rayon.cardL,
          padding: sp[4],
          gap: sp[4],
          shadowColor: "#0F1B3D",
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.06,
          shadowRadius: 16,
          elevation: 3,
          marginBottom: sp[5],
        }}
      >
        <Text variante="sousTitre">Nouvelle alerte</Text>

        {/* Quartier — chips depuis l'API */}
        <View style={{ gap: sp[2] }}>
          <Text variante="label">Quartier</Text>
          <QueryState query={districts}>
            {(liste) => (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
                {liste.map((d) => (
                  <Chip
                    key={d.slug}
                    titre={d.name}
                    actif={districtsSel.includes(d.slug)}
                    onPress={() => basculerDistrict(d.slug)}
                  />
                ))}
              </View>
            )}
          </QueryState>
        </View>

        {/* Budget max — champ texte stylisé "15 000 FCFA / mois" */}
        <View style={{ gap: sp[2] }}>
          <Text variante="label">Budget max</Text>
          <Controller
            control={control}
            name="rent_max"
            render={({ field }) => (
              <TextField
                label=""
                value={field.value}
                onChangeText={field.onChange}
                keyboardType="number-pad"
                placeholder="15 000 FCFA / mois"
              />
            )}
          />
        </View>

        {/* Type — chips */}
        <View style={{ gap: sp[2] }}>
          <Text variante="label">Type</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
            {TYPES.map((tp) => (
              <Chip
                key={tp}
                titre={t.typeChambre[tp] ?? tp}
                actif={typesSel.includes(tp)}
                onPress={() => basculerType(tp)}
              />
            ))}
          </View>
        </View>

        {/* CTA */}
        <Button
          titre="+ Créer l'alerte"
          chargement={creer.isPending}
          onPress={handleSubmit(soumettre)}
        />
      </View>

      {/* ── Section alertes actives (conforme maquette) ── */}
      <QueryState
        query={requete}
        vide={{
          quand: (data) => data.length === 0,
          titre: "Aucune alerte active",
          texte: "Crée ta première alerte ci-dessus.",
        }}
      >
        {(alertes) => (
          <View style={{ gap: sp[3] }}>
            <Text variante="label" style={{ marginBottom: sp[1] }}>Alertes actives</Text>
            {alertes.map((alerte) => (
              <AlerteCard
                key={alerte.id}
                alerte={alerte}
                onSupprimer={() => confirmerSuppression(alerte.id)}
                onModifier={() => router.push(`/modifier-alerte/${alerte.id}` as never)}
                supprimerEnCours={supprimer.isPending && supprimer.variables === alerte.id}
              />
            ))}
          </View>
        )}
      </QueryState>
    </Screen>
  );
}

/** Carte d'une alerte active — conforme à la maquette (toggle vert à droite, critères en dessous). */
function AlerteCard({
  alerte,
  onSupprimer,
  onModifier,
  supprimerEnCours,
}: {
  alerte: Alerte;
  onSupprimer: () => void;
  onModifier: () => void;
  supprimerEnCours: boolean;
}) {
  const { c } = useTheme();
  const modifier = useModifierAlerte(alerte.id);

  // Résumé textuel : "Banikanni · Entrée-coucher" comme dans la maquette
  const parties: string[] = [];
  if (alerte.district?.length) parties.push(alerte.district.join(", "));
  if (alerte.type?.length) parties.push(alerte.type.map((tp) => t.typeChambre[tp] ?? tp).join(", "));
  const titre = parties.join(" · ") || "Toutes les chambres";

  const criteres: string[] = [];
  if (alerte.rent_max) criteres.push(`≤ ${alerte.rent_max.toLocaleString("fr-BJ")} F`);
  if (alerte.bathroom) criteres.push("Douche interne");

  return (
    <View
      style={{
        backgroundColor: c.surface,
        borderRadius: rayon.card,
        padding: sp[4],
        gap: sp[3],
        shadowColor: "#0F1B3D",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.04,
        shadowRadius: 8,
        elevation: 1,
      }}
    >
      <View style={{ flexDirection: "row", alignItems: "flex-start", gap: sp[3] }}>
        {/* Icône alerte (carré arrondi bleu pâle) */}
        <View
          style={{
            width: 40,
            height: 40,
            borderRadius: 12,
            backgroundColor: c.primarySoft,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <View style={{ width: 18, height: 14, borderRadius: 3, backgroundColor: c.primary, opacity: 0.8 }} />
        </View>

        <View style={{ flex: 1 }}>
          <Text variante="corpsGras" numberOfLines={2}>{titre}</Text>
          {criteres.length ? (
            <Text variante="legende" muted>{criteres.join(" · ")}</Text>
          ) : null}
        </View>

        {/* Toggle actif/pause — vert Google-style via SwitchRow interne */}
        <SwitchRow
          titre=""
          valeur={alerte.is_active}
          onChange={(v) =>
            void modifier.mutate({
              is_active: v,
              district: alerte.district,
              type: alerte.type,
              rent_max: alerte.rent_max,
              bathroom: alerte.bathroom,
              fenced: alerte.fenced,
            } as AlerteEntree)
          }
        />
      </View>

      {/* Actions secondaires */}
      <View style={{ flexDirection: "row", gap: sp[2] }}>
        <Button titre="Modifier" variante="secondaire" taille="compacte" style={{ flex: 1 }} onPress={onModifier} />
        <Button titre="Supprimer" variante="danger" taille="compacte" style={{ flex: 1 }} chargement={supprimerEnCours} onPress={onSupprimer} />
      </View>
    </View>
  );
}
