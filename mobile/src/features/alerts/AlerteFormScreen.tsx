import { useEffect } from "react";
import { View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useRouter } from "expo-router";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { useDistricts } from "@/features/listings/queries";
import { useAlertes, useCreerAlerte, useModifierAlerte } from "./queries";

const TYPES = ["single", "entree_coucher", "chambre_salon", "studio"] as const;

const schema = z.object({
  rent_max: z.coerce.number().min(0).optional().or(z.literal("")),
  bathroom: z.boolean(),
  fenced: z.boolean(),
  district: z.array(z.string()),
  type: z.array(z.string()),
});

type Valeurs = {
  rent_max: number | "" | undefined;
  bathroom: boolean;
  fenced: boolean;
  district: string[];
  type: string[];
};

/**
 * Formulaire de création et de modification d'une alerte (EF-ALR-01).
 * Route /nouvelle-alerte → création ; /modifier-alerte/[id] → préremplissage + PATCH.
 */
export function AlerteFormScreen() {
  const { c } = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string }>();
  const id = params.id;
  const estModification = !!id;

  const districts = useDistricts();
  const alertes = useAlertes(estModification);
  const creer = useCreerAlerte();
  const modifier = useModifierAlerte(id ?? "");
  const mutation = estModification ? modifier : creer;

  const { control, handleSubmit, reset, watch, setValue, formState: { errors } } = useForm<Valeurs>({
    resolver: zodResolver(schema),
    defaultValues: { rent_max: "", bathroom: false, fenced: false, district: [], type: [] },
  });

  // Préremplissage en mode modification
  useEffect(() => {
    if (!estModification || !alertes.data) return;
    const alerte = alertes.data.find((a) => a.id === id);
    if (!alerte) return;
    reset({
      rent_max: alerte.rent_max ?? "",
      bathroom: alerte.bathroom ?? false,
      fenced: alerte.fenced ?? false,
      district: alerte.district ?? [],
      type: alerte.type ?? [],
    });
  }, [estModification, id, alertes.data, reset]);

  const districtsSel = watch("district");
  const typesSel = watch("type");
  const basculerDistrict = (slug: string) =>
    setValue("district", districtsSel.includes(slug) ? districtsSel.filter((d) => d !== slug) : [...districtsSel, slug]);
  const basculerType = (tp: string) =>
    setValue("type", typesSel.includes(tp) ? typesSel.filter((tt) => tt !== tp) : [...typesSel, tp]);

  const soumettre = (v: Valeurs) => {
    const corps = {
      rent_max: v.rent_max ? Number(v.rent_max) : undefined,
      bathroom: v.bathroom || undefined,
      fenced: v.fenced || undefined,
      district: v.district.length ? v.district : undefined,
      type: v.type.length ? v.type : undefined,
    };
    mutation.mutate(corps as never, { onSuccess: () => router.back() });
  };

  return (
    <Screen scroll footer={<Button titre={estModification ? t.commun.enregistrer : "Créer l'alerte"} chargement={mutation.isPending} onPress={handleSubmit(soumettre)} />}>
      <Text variante="titre">{estModification ? "Modifier l'alerte" : "Nouvelle alerte"}</Text>
      <Text muted>Définis les critères qui te correspondent. Laisse vide pour recevoir toutes les annonces.</Text>

      {/* Loyer maximum */}
      <Controller
        control={control}
        name="rent_max"
        render={({ field }) => (
          <TextField
            label="Loyer maximum (FCFA)"
            value={field.value ? String(field.value) : ""}
            onChangeText={(v) => field.onChange(v === "" ? "" : Number(v))}
            keyboardType="number-pad"
            erreur={errors.rent_max?.message}
          />
        )}
      />

      {/* Type de chambre */}
      <View style={{ gap: sp[2] }}>
        <Text variante="label">Type de chambre</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          {TYPES.map((tp) => (
            <Chip key={tp} titre={t.typeChambre[tp] ?? tp} actif={typesSel.includes(tp)} onPress={() => basculerType(tp)} />
          ))}
        </View>
      </View>

      {/* Quartiers */}
      <QueryState query={districts}>
        {(liste) => (
          <View style={{ gap: sp[2] }}>
            <Text variante="label">Quartiers</Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
              {liste.map((d) => (
                <Chip key={d.slug} titre={d.name} actif={districtsSel.includes(d.slug)} onPress={() => basculerDistrict(d.slug)} />
              ))}
            </View>
          </View>
        )}
      </QueryState>

      {/* Équipements */}
      <View style={{ gap: sp[1], borderWidth: 1, borderColor: c.border, borderRadius: 16, paddingHorizontal: sp[4], backgroundColor: c.surface }}>
        <Controller
          control={control}
          name="bathroom"
          render={({ field }) => (
            <SwitchRow titre="Douche interne" aide="Sanitaires privatifs dans la chambre" valeur={field.value} onChange={field.onChange} />
          )}
        />
        <Controller
          control={control}
          name="fenced"
          render={({ field }) => (
            <SwitchRow titre="Clôturé" aide="Concession fermée avec portail" valeur={field.value} onChange={field.onChange} />
          )}
        />
      </View>

      {mutation.error ? (
        <Text variante="legende" couleur={c.danger} accessibilityLiveRegion="polite">
          {isApiError(mutation.error) ? messageErreur(mutation.error.code, mutation.error.message) : t.commun.erreurGenerique}
        </Text>
      ) : null}
    </Screen>
  );
}
