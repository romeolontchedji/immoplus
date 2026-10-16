import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { View } from "react-native";
import { useRouter } from "expo-router";
import { z } from "zod";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { t } from "@/i18n/fr";
import { useBrouillon } from "./brouillon";
import { EntetePublication } from "./EntetePublication";

const TYPES = ["single", "entree_coucher", "chambre_salon", "studio"] as const;
const CAUTIONS = ["1", "2", "3"] as const;

const schema = z.object({
  title: z.string().trim().min(3, "Au moins 3 caractères.").max(120, "120 caractères au plus."),
  room_type: z.enum(TYPES, { error: "Choisis un type." }),
  rent_amount: z.coerce.number({ invalid_type_error: "Obligatoire." }).min(1000, "1 000 F minimum.").max(999_999, "Trop élevé."),
  deposit_months: z.coerce.number().min(1).max(6),
  is_available: z.boolean(),
});

type Valeurs = z.infer<typeof schema>;

/**
 * Étape 1/4 — Infos de base (EF-ANN-02).
 * Conforme à la maquette « Mobile · Publier 1 4@1x.png » :
 * - Titre, type (chips pilule), quartier + loyer côte à côte, caution + toggle "Disponible"
 * - Barre de progression 4 segments (1 bleu)
 * - Footer : "Continuer"
 */
export function InfosStep() {
  const { c } = useTheme();
  const router = useRouter();
  const { brouillon, maj } = useBrouillon();

  const { control, handleSubmit, watch, setValue, formState: { errors } } = useForm<Valeurs>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: brouillon.title ?? "",
      room_type: (brouillon.room_type as typeof TYPES[number]) ?? undefined,
      rent_amount: brouillon.rent_amount ?? (undefined as unknown as number),
      deposit_months: brouillon.deposit_months ?? 2,
      is_available: !brouillon.available_from || brouillon.available_from <= new Date().toISOString().slice(0, 10),
    },
  });

  const typeSel = watch("room_type");
  const caution = watch("deposit_months");

  const suivant = (v: Valeurs) => {
    maj({
      title: v.title,
      room_type: v.room_type,
      rent_amount: v.rent_amount,
      deposit_months: v.deposit_months,
      advance_months: 1,
      available_from: v.is_available ? new Date().toISOString().slice(0, 10) : undefined,
    });
    router.push("/pro/nouvelle-annonce/localisation" as never);
  };

  return (
    <Screen scroll footer={<Button titre="Continuer" onPress={handleSubmit(suivant)} />}>
      <EntetePublication etape={1} total={4} />

      <Text variante="titre" style={{ marginTop: sp[2] }}>Parle-nous de ta chambre</Text>
      <Text muted>Les infos que les étudiants cherchent en premier.</Text>

      {/* Titre */}
      <Controller
        control={control}
        name="title"
        render={({ field }) => (
          <TextField
            label="Titre"
            value={field.value}
            onChangeText={field.onChange}
            placeholder="Chambre-salon à Banikanni"
            erreur={errors.title?.message}
          />
        )}
      />

      {/* Type — chips (actif = bleu cobalt) */}
      <View style={{ gap: sp[2] }}>
        <Text variante="label">Type</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          {TYPES.map((tp) => (
            <Chip
              key={tp}
              titre={t.typeChambre[tp] ?? tp}
              actif={typeSel === tp}
              onPress={() => setValue("room_type", tp)}
            />
          ))}
        </View>
        {errors.room_type ? <Text variante="legende" couleur={c.danger}>{errors.room_type.message}</Text> : null}
      </View>

      {/* Loyer */}
      <Controller
        control={control}
        name="rent_amount"
        render={({ field }) => (
          <TextField
            label="Loyer / mois"
            value={field.value ? String(field.value) : ""}
            onChangeText={(v) => field.onChange(v === "" ? undefined : Number(v))}
            keyboardType="number-pad"
            placeholder="18 000 F"
            erreur={errors.rent_amount?.message}
          />
        )}
      />

      {/* Caution + toggle Disponible côte à côte (conforme maquette) */}
      <View style={{ flexDirection: "row", gap: sp[3], alignItems: "flex-end" }}>
        <View style={{ flex: 1, gap: sp[2] }}>
          <Text variante="label">Caution</Text>
          <View style={{ flexDirection: "row", gap: sp[2] }}>
            {CAUTIONS.map((nb) => (
              <Chip
                key={nb}
                titre={`${nb} mois`}
                actif={caution === Number(nb)}
                onPress={() => setValue("deposit_months", Number(nb))}
              />
            ))}
          </View>
        </View>
        <Controller
          control={control}
          name="is_available"
          render={({ field }) => (
            <SwitchRow titre="Disponible" valeur={field.value} onChange={field.onChange} />
          )}
        />
      </View>
    </Screen>
  );
}
