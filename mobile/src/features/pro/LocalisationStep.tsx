import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { View } from "react-native";
import { useRouter } from "expo-router";
import { z } from "zod";
import { sp } from "@/ui/theme/tokens";
import { Chip } from "@/ui/components/Chip";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { Button } from "@/ui/components/Button";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { t } from "@/i18n/fr";
import { useDistricts } from "@/features/listings/queries";
import { useBrouillon } from "./brouillon";
import { EntetePublication } from "./EntetePublication";

const schema = z.object({
  district: z.string({ error: "Choisis un quartier." }).min(1, "Obligatoire."),
  landmark_text: z.string().trim().min(3, "Décris un repère.").max(200),
  address_private: z.string().trim().min(3, "Adresse précise obligatoire.").max(300),
});

type Valeurs = z.infer<typeof schema>;

/**
 * Étape 2/4 — Localisation (EF-ANN-03).
 * Quartier en chips + repère campus + adresse confidentielle.
 * L'adresse privée n'est jamais affichée aux locataires (serveur l'exclut des réponses publiques).
 */
export function LocalisationStep() {
  const { c } = useTheme();
  const router = useRouter();
  const { brouillon, maj } = useBrouillon();
  const districts = useDistricts();

  const { control, handleSubmit, watch, setValue, formState: { errors } } = useForm<Valeurs>({
    resolver: zodResolver(schema),
    defaultValues: {
      district: brouillon.district ?? "",
      landmark_text: brouillon.landmark_text ?? "",
      address_private: brouillon.address_private ?? "",
    },
  });

  const districtSel = watch("district");

  const suivant = (v: Valeurs) => {
    maj({ district: v.district, landmark_text: v.landmark_text, address_private: v.address_private, latitude: "0", longitude: "0" });
    router.push("/pro/nouvelle-annonce/equipements" as never);
  };

  return (
    <Screen scroll footer={<Button titre="Continuer" onPress={handleSubmit(suivant)} />}>
      <EntetePublication etape={2} total={4} />

      <Text variante="titre" style={{ marginTop: sp[2] }}>Où se trouve-t-elle ?</Text>
      <Text muted>Le quartier est public. L'adresse précise reste confidentielle.</Text>

      {/* Quartier — chips */}
      <View style={{ gap: sp[2] }}>
        <Text variante="label">Quartier</Text>
        <QueryState query={districts}>
          {(liste) => (
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
              {liste.map((d) => (
                <Chip
                  key={d.slug}
                  titre={d.name}
                  actif={districtSel === d.slug}
                  onPress={() => setValue("district", d.slug)}
                />
              ))}
            </View>
          )}
        </QueryState>
        {errors.district ? <Text variante="legende" couleur={c.danger}>{errors.district.message}</Text> : null}
      </View>

      {/* Repère campus */}
      <Controller
        control={control}
        name="landmark_text"
        render={({ field }) => (
          <TextField
            label="Repère (visible par les étudiants)"
            value={field.value}
            onChangeText={field.onChange}
            placeholder="7 min à pied de l'UP"
            erreur={errors.landmark_text?.message}
          />
        )}
      />

      {/* Adresse confidentielle */}
      <Controller
        control={control}
        name="address_private"
        render={({ field }) => (
          <TextField
            label="Adresse précise (confidentielle)"
            value={field.value}
            onChangeText={field.onChange}
            placeholder="Rue de l'Amitié, porte bleue…"
            erreur={errors.address_private?.message}
          />
        )}
      />
    </Screen>
  );
}
