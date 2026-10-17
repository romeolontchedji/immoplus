import { useMemo } from "react";
import { Pressable, ScrollView } from "react-native";
import { t } from "@/i18n/fr";
import { Chip } from "@/ui/components/Chip";
import { Text } from "@/ui/components/Text";
import { sp } from "@/ui/theme/tokens";
import { FILTRES_VIDES, filtresActifs, useFiltres } from "./filtres";
import { useDistricts } from "./queries";

/** Rangée des filtres actifs, chacun retirable d'un toucher, et « Tout effacer ». Rien n'est affiché sans filtre. */
export function FiltresActifs() {
  const { filtres, definir } = useFiltres();
  const districts = useDistricts();
  const noms = useMemo(() => Object.fromEntries((districts.data ?? []).map((d) => [d.slug, d.name])), [districts.data]);
  const actifs = filtresActifs(filtres, noms, (tp) => t.typeChambre[tp] ?? tp);
  if (!actifs.length) return null;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: sp[2], alignItems: "center", paddingRight: sp[2] }}>
      {actifs.map((a) => (
        <Chip key={a.cle} titre={a.libelle} actif retirable onPress={() => definir(a.retirer(filtres))} />
      ))}
      <Pressable
        accessibilityRole="button"
        onPress={() => definir({ ...FILTRES_VIDES, q: filtres.q, sort: filtres.sort })}
        hitSlop={8}
        style={{ paddingHorizontal: sp[2], minHeight: 40, justifyContent: "center" }}
      >
        <Text variante="lien" style={{ fontSize: 14, fontWeight: "700" }}>Tout effacer</Text>
      </Pressable>
    </ScrollView>
  );
}
