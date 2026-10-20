import { View } from "react-native";
import { useRouter } from "expo-router";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { ListeDeroulante } from "@/ui/components/ListeDeroulante";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { colors, sp } from "@/ui/theme/tokens";
import { LIBELLES_COMPTEUR, LIBELLES_CUISINE, LIBELLES_EAU } from "@/features/listings/filtres";
import { useBrouillon } from "./brouillon";
import { EntetePublication } from "./EntetePublication";

const options = (libelles: Record<string, string>) => Object.entries(libelles).map(([valeur, libelle]) => ({ valeur, libelle }));

/**
 * Étape Équipements (plan v3, C2) : électricité (compteur personnel, décompteur, partagé), eau (compteur personnel,
 * décompteur, eau courante, forage, puits), cuisine, en listes déroulantes ; douche interne et clôture en cases.
 * Les champs remplacent l'ancien grand texte : les locataires filtrent directement dessus.
 */
export function EquipementsStep() {
  const router = useRouter();
  const { brouillon, maj } = useBrouillon();
  const complet = !!brouillon.water_sources?.length && !!brouillon.electricity_meter && !!brouillon.kitchen;

  return (
    <Screen
      scroll
      footer={
        <Button
          titre={complet ? "Continuer" : "Indique l'électricité, l'eau et la cuisine"}
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
      <Text muted>Les locataires filtrent sur ces critères : sois précis.</Text>

      <View style={{ gap: sp[5] }}>
        <ListeDeroulante label="Électricité" placeholder="Choisis" options={options(LIBELLES_COMPTEUR)} valeurs={brouillon.electricity_meter ? [brouillon.electricity_meter] : []} onChange={(v) => maj({ electricity_meter: v[0] })} />
        <ListeDeroulante label="Eau (plusieurs choix possibles)" placeholder="Choisis" multiple options={options(LIBELLES_EAU)} valeurs={brouillon.water_sources ?? []} onChange={(v) => maj({ water_sources: v })} />
        <ListeDeroulante label="Cuisine" placeholder="Choisis" options={options(LIBELLES_CUISINE)} valeurs={brouillon.kitchen ? [brouillon.kitchen] : []} onChange={(v) => maj({ kitchen: v[0] })} />
        <View style={{ gap: sp[2] }}>
          <Text variante="label" muted>Confort</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
            <Chip titre="Douche interne" actif={!!brouillon.has_private_bathroom} onPress={() => maj({ has_private_bathroom: !brouillon.has_private_bathroom })} />
            <Chip titre="Cour clôturée" actif={!!brouillon.is_fenced} onPress={() => maj({ is_fenced: !brouillon.is_fenced })} />
          </View>
        </View>
      </View>
      {!complet ? <Text variante="legende" couleur={colors.textMuted}>Ces trois informations sont obligatoires.</Text> : null}
    </Screen>
  );
}
