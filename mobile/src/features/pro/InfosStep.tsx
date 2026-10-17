import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
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
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { TYPES_OFFICIELS } from "@/features/listings/queries";
import { useBrouillon } from "./brouillon";
import { useProposerType, useTypesChambrePro } from "./queries";
import { EntetePublication } from "./EntetePublication";

const CAUTIONS = ["1", "2", "3"] as const;

const schema = z.object({
  title: z.string().trim().min(3, "Au moins 3 caractères.").max(120, "120 caractères au plus."),
  room_type: z.string({ error: "Choisis un type." }).min(1, "Choisis un type."),
  rent_amount: z.coerce.number({ error: "Obligatoire." }).min(1000, "1 000 F minimum.").max(999_999, "Trop élevé."),
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

  const { control, handleSubmit, watch, setValue, formState: { errors } } = useForm<z.input<typeof schema>, unknown, Valeurs>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: brouillon.title ?? "",
      room_type: brouillon.room_type ?? "",
      rent_amount: brouillon.rent_amount ?? (undefined as unknown as number),
      deposit_months: brouillon.deposit_months ?? 2,
      is_available: !brouillon.available_from || brouillon.available_from <= new Date().toISOString().slice(0, 10),
    },
  });

  const typeSel = watch("room_type");
  const typesPro = useTypesChambrePro();
  const types = typesPro.data ?? TYPES_OFFICIELS.map((x) => ({ ...x, status: "approved" as const }));
  const proposer = useProposerType();
  const [autre, setAutre] = useState<string | null>(null); // champ « Autre type » ouvert

  const ajouterType = () => {
    if (!autre?.trim()) return;
    proposer.mutate(autre.trim(), {
      onSuccess: (tp) => {
        setValue("room_type", tp.slug, { shouldValidate: true });
        setAutre(null);
      },
    });
  };
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
      <EntetePublication etape={1} total={6} />

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
          {types.map((tp) => (
            <Chip
              key={tp.slug}
              titre={tp.status === "pending" ? `${tp.label} (en validation)` : tp.label}
              actif={typeSel === tp.slug}
              onPress={() => setValue("room_type", tp.slug, { shouldValidate: true })}
            />
          ))}
          <Chip titre="Autre…" actif={autre !== null} onPress={() => setAutre(autre === null ? "" : null)} />
        </View>
        {autre !== null ? (
          <View style={{ gap: sp[2] }}>
            <TextField
              label="Nouveau type"
              value={autre}
              onChangeText={setAutre}
              placeholder="Ex. appartement meublé"
              maxLength={40}
              autoFocus
              aide="Tu peux l'utiliser tout de suite ; l'équipe le valide avant qu'il apparaisse dans les filtres."
              erreur={proposer.error ? (isApiError(proposer.error) ? messageErreur(proposer.error.code, proposer.error.message) : t.erreurs.network) : undefined}
            />
            <Button titre="Ajouter ce type" variante="secondaire" taille="compacte" chargement={proposer.isPending} disabled={(autre ?? "").trim().length < 3} onPress={ajouterType} />
          </View>
        ) : null}
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
