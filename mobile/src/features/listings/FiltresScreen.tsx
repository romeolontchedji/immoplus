import { View } from "react-native";
import { useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Pressable } from "react-native";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { CIBLE_MIN, rayon, sp } from "@/ui/theme/tokens";
import { t } from "@/i18n/fr";
import { FILTRES_VIDES, nombreDeFiltres, useFiltres, type Filtres } from "./filtres";
import { useDistricts } from "./queries";

const TYPES = ["single", "entree_coucher", "chambre_salon", "studio"] as const;
const DISTANCES = [
  { val: 500, label: "5 min" },
  { val: 1000, label: "10 min" },
  { val: 2000, label: "20 min" },
] as const;

/**
 * Écran Filtres avancés (EF-REC-05).
 * Conforme à la maquette « Mobile · Filtres@1x.png » :
 * - Titre "Filtres" + lien "Réinitialiser" bleu en haut à droite
 * - Sections avec labels uppercase gris
 * - Chips pilule (actif = bleu cobalt + blanc)
 * - Budget = champ texte (slider non disponible sans lib native)
 * - Bouton "Voir N chambres" bleu cobalt en bas (footer)
 */
export function FiltresScreen() {
  const { c } = useTheme();
  const router = useRouter();
  const { filtres, definir, reinitialiser } = useFiltres();
  const districts = useDistricts();

  const { control, handleSubmit, watch, setValue } = useForm<Filtres>({
    defaultValues: filtres,
  });

  const districtsSel = watch("district");
  const typesSel = watch("type");
  const distanceSel = watch("max_distance_m");
  const bathroomVal = watch("bathroom");
  const fencedVal = watch("fenced");

  const basculerDistrict = (slug: string) =>
    setValue("district", districtsSel.includes(slug)
      ? districtsSel.filter((d) => d !== slug)
      : [...districtsSel, slug]);

  const basculerType = (tp: string) =>
    setValue("type", typesSel.includes(tp)
      ? typesSel.filter((tt) => tt !== tp)
      : [...typesSel, tp]);

  const appliquer = (v: Filtres) => { definir(v); router.back(); };
  const nb = nombreDeFiltres(filtres);

  return (
    <Screen
      scroll
      footer={
        <Button
          titre={nb ? `Voir ${nb} chambres` : "Voir les résultats"}
          onPress={handleSubmit(appliquer)}
        />
      }
    >
      {/* En-tête : Filtres + Réinitialiser bleu (conforme maquette) */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: sp[4] }}>
        <Text variante="titreSection">Filtres</Text>
        <Pressable
          accessibilityRole="button"
          onPress={() => { reinitialiser(); router.back(); }}
          style={{ minHeight: CIBLE_MIN, justifyContent: "center", paddingLeft: sp[4] }}
        >
          <Text variante="lien">Réinitialiser</Text>
        </Pressable>
      </View>

      {/* ── Quartier ── */}
      <View style={{ gap: sp[3], marginBottom: sp[4] }}>
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

      {/* ── Budget max ── */}
      <View style={{ gap: sp[3], marginBottom: sp[4] }}>
        <Controller
          control={control}
          name="rent_max"
          render={({ field }) => (
            <TextField
              label={field.value ? `Budget max · ${Number(field.value).toLocaleString("fr-BJ")} F` : "Budget max"}
              value={field.value ? String(field.value) : ""}
              onChangeText={(v) => field.onChange(v === "" ? undefined : Number(v))}
              keyboardType="number-pad"
              placeholder="Ex : 15 000"
            />
          )}
        />
      </View>

      {/* ── Type ── */}
      <View style={{ gap: sp[3], marginBottom: sp[4] }}>
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

      {/* ── Distance de l'UP (campus) ── */}
      <View style={{ gap: sp[3], marginBottom: sp[4] }}>
        <Text variante="label">Distance de l'UP</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          {DISTANCES.map(({ val, label }) => (
            <Chip
              key={val}
              titre={label}
              actif={distanceSel === val}
              onPress={() => setValue("max_distance_m", distanceSel === val ? undefined : val)}
            />
          ))}
        </View>
      </View>

      {/* ── Équipements ── */}
      <View style={{ gap: sp[2], marginBottom: sp[4] }}>
        <Text variante="label">Équipements</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          <Chip
            titre="Douche interne"
            actif={!!bathroomVal}
            onPress={() => setValue("bathroom", !bathroomVal)}
          />
          <Chip
            titre="Eau + électricité"
            actif={false}
            onPress={() => {/* champ non exposé dans Filtres, placeholder maquette */}}
          />
          <Chip
            titre="Cour clôturée"
            actif={!!fencedVal}
            onPress={() => setValue("fenced", !fencedVal)}
          />
        </View>
      </View>

      {/* ── Confiance ── */}
      <View style={{ gap: sp[2] }}>
        <Text variante="label">Confiance</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          <Chip titre="Gérant vérifié" actif={false} onPress={() => {}} />
          <Chip titre="Avec vidéo" actif={false} onPress={() => {}} />
        </View>
      </View>
    </Screen>
  );
}
