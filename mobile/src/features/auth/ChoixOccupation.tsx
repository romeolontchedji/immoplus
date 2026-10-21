import { View } from "react-native";
import type { components } from "@/api/genere/api";
import { Chip } from "@/ui/components/Chip";
import { Text } from "@/ui/components/Text";
import { sp } from "@/ui/theme/tokens";

export type Occupation = components["schemas"]["OccupationEnum"];

/** Libellés de « Tu es » (décision V2) : mêmes valeurs que `apps.accounts.enums.Occupation`. */
export const OCCUPATIONS: { valeur: Occupation; libelle: string }[] = [
  { valeur: "student_up", libelle: "Étudiant(e) à l'UP" },
  { valeur: "student_other", libelle: "Étudiant(e) ailleurs" },
  { valeur: "employee", libelle: "Salarié(e)" },
  { valeur: "self_employed", libelle: "Indépendant(e)" },
  { valeur: "other", libelle: "Autre" },
];

/** Question facultative : un second appui sur la pastille choisie retire la réponse. */
export function ChoixOccupation({ valeur, onChange }: { valeur: Occupation | null; onChange: (v: Occupation | null) => void }) {
  return (
    <View style={{ gap: sp[2] }}>
      <Text variante="label">Tu es (facultatif)</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
        {OCCUPATIONS.map((o) => (
          <Chip key={o.valeur} titre={o.libelle} actif={valeur === o.valeur} onPress={() => onChange(valeur === o.valeur ? null : o.valeur)} />
        ))}
      </View>
    </View>
  );
}
