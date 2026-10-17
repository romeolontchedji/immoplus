import { View } from "react-native";
import { useRouter } from "expo-router";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { colors, sp } from "@/ui/theme/tokens";
import { useBrouillon } from "./brouillon";
import { EntetePublication } from "./EntetePublication";

const EAUX = [
  { val: "running", label: "Eau courante" },
  { val: "borehole", label: "Forage" },
  { val: "well", label: "Puits" },
] as const;
const COMPTEURS = [
  { val: "individual", label: "Compteur individuel" },
  { val: "shared", label: "Compteur partagé" },
] as const;

function Bloc({ titre, aide, children }: { titre: string; aide?: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: sp[2] }}>
      <Text variante="label" muted>{titre}</Text>
      {aide ? <Text variante="legende" muted>{aide}</Text> : null}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>{children}</View>
    </View>
  );
}

/**
 * Étape Équipements (EF-ANN-04) : douche interne, clôture, source d'eau, compteur électrique. Ces champs sont exigés par
 * `POST /v1/pro/listings` ; l'annonce est créée côté serveur à l'étape suivante (description).
 */
export function EquipementsStep() {
  const router = useRouter();
  const { brouillon, maj } = useBrouillon();
  const complet = !!brouillon.water_source && !!brouillon.electricity_meter;

  return (
    <Screen
      scroll
      footer={
        <Button
          titre={complet ? "Continuer" : "Choisis l'eau et le compteur"}
          disabled={!complet}
          onPress={() => {
            maj({ has_private_bathroom: !!brouillon.has_private_bathroom, is_fenced: !!brouillon.is_fenced });
            router.push("/pro/nouvelle-annonce/description" as never);
          }}
        />
      }
    >
      <EntetePublication etape={3} total={6} />
      <Text variante="titre" style={{ marginTop: sp[2] }}>Qu’est-ce qu’il y a ?</Text>
      <Text muted>Les étudiants filtrent sur ces critères : sois précis.</Text>

      <View style={{ gap: sp[5] }}>
        <Bloc titre="Confort">
          <Chip titre="Douche interne" actif={!!brouillon.has_private_bathroom} onPress={() => maj({ has_private_bathroom: !brouillon.has_private_bathroom })} />
          <Chip titre="Cour clôturée" actif={!!brouillon.is_fenced} onPress={() => maj({ is_fenced: !brouillon.is_fenced })} />
        </Bloc>
        <Bloc titre="Eau" aide="Obligatoire">
          {EAUX.map((e) => (
            <Chip key={e.val} titre={e.label} actif={brouillon.water_source === e.val} onPress={() => maj({ water_source: e.val })} />
          ))}
        </Bloc>
        <Bloc titre="Électricité" aide="Obligatoire">
          {COMPTEURS.map((e) => (
            <Chip key={e.val} titre={e.label} actif={brouillon.electricity_meter === e.val} onPress={() => maj({ electricity_meter: e.val })} />
          ))}
        </Bloc>
      </View>
      {!complet ? <Text variante="legende" couleur={colors.textMuted}>Indique la source d’eau et le type de compteur pour continuer.</Text> : null}
    </Screen>
  );
}
