import { TextInput, View } from "react-native";
import { francs } from "@/lib/format";
import { t } from "@/i18n/fr";
import { Chip } from "@/ui/components/Chip";
import { QueryState } from "@/ui/components/States";
import { Text } from "@/ui/components/Text";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import type { Filtres } from "@/features/listings/filtres";
import { useDistricts } from "@/features/listings/queries";
import type { Alerte, AlerteEntree } from "./queries";

const TYPES = ["single", "entree_coucher", "chambre_salon", "studio"] as const;
const BUDGETS = [10_000, 15_000, 20_000, 30_000] as const;
const DISTANCES = [500, 1000, 2000] as const;

/** Critères d'une alerte, au format de l'API (`AlerteIn`). */
export type Criteres = {
  district_ids: string[];
  room_types: string[];
  max_rent: number | null;
  private_bathroom_required: boolean;
  max_distance_m: number | null;
};

export const CRITERES_VIDES: Criteres = { district_ids: [], room_types: [], max_rent: null, private_bathroom_required: false, max_distance_m: null };

export const criteresDe = (a: Alerte): Criteres => ({
  district_ids: a.district_ids ?? [],
  room_types: a.room_types ?? [],
  max_rent: a.max_rent ?? null,
  private_bathroom_required: !!a.private_bathroom_required,
  max_distance_m: a.max_distance_m ?? null,
});

export const versCorps = (c: Criteres, label = ""): AlerteEntree => ({ ...c, label });

/** Reprend la recherche en cours (slugs de quartier → identifiants) pour « Créer une alerte pour cette recherche ». */
export function criteresDepuisFiltres(f: Filtres, quartiers: { id: string; slug: string }[]): Criteres {
  return {
    district_ids: quartiers.filter((q) => f.district.includes(q.slug)).map((q) => q.id),
    room_types: f.type,
    max_rent: f.rent_max ?? null,
    private_bathroom_required: !!f.bathroom,
    max_distance_m: f.max_distance_m ?? null,
  };
}

/** Résumé lisible : « Banikanni, Titirou · Entrée-coucher · ≤ 15 000 F ». */
export function resumeCriteres(c: Criteres, noms: Record<string, string>): { titre: string; details: string } {
  const lieux = c.district_ids.map((id) => noms[id]).filter(Boolean).join(", ");
  const types = c.room_types.map((tp) => t.typeChambre[tp] ?? tp).join(", ");
  const details = [
    c.max_rent ? `≤ ${francs(c.max_rent)}` : null,
    c.max_distance_m ? `≤ ${c.max_distance_m} m de l'UP` : null,
    c.private_bathroom_required ? "Douche interne" : null,
  ].filter(Boolean).join(" · ");
  return { titre: [lieux, types].filter(Boolean).join(" · ") || "Toutes les chambres", details };
}

const basculer = (liste: string[], v: string) => (liste.includes(v) ? liste.filter((x) => x !== v) : [...liste, v]);

function Bloc({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: sp[2] }}>
      <Text variante="label" muted>{titre}</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>{children}</View>
    </View>
  );
}

/** Éditeur des critères d'alerte : mêmes pastilles que la feuille de filtres. */
export function EditeurCriteres({ valeur, onChange }: { valeur: Criteres; onChange: (c: Criteres) => void }) {
  const districts = useDistricts();
  const maj = (p: Partial<Criteres>) => onChange({ ...valeur, ...p });
  const budgetLibre = valeur.max_rent !== null && !BUDGETS.includes(valeur.max_rent as (typeof BUDGETS)[number]);

  return (
    <View style={{ gap: sp[5] }}>
      <View style={{ gap: sp[2] }}>
        <Text variante="label" muted>Quartiers</Text>
        <QueryState query={districts}>
          {(liste) => (
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
              {liste.map((d) => (
                <Chip key={d.id} titre={d.name} actif={valeur.district_ids.includes(d.id)} onPress={() => maj({ district_ids: basculer(valeur.district_ids, d.id) })} />
              ))}
            </View>
          )}
        </QueryState>
      </View>

      <Bloc titre="Type">
        {TYPES.map((tp) => (
          <Chip key={tp} titre={t.typeChambre[tp] ?? tp} actif={valeur.room_types.includes(tp)} onPress={() => maj({ room_types: basculer(valeur.room_types, tp) })} />
        ))}
      </Bloc>

      <View style={{ gap: sp[2] }}>
        <Text variante="label" muted>{valeur.max_rent ? `Budget max · ${francs(valeur.max_rent)}` : "Budget max"}</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          {BUDGETS.map((b) => (
            <Chip key={b} titre={`≤ ${francs(b)}`} actif={valeur.max_rent === b} onPress={() => maj({ max_rent: valeur.max_rent === b ? null : b })} />
          ))}
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", minHeight: 52, borderWidth: 1.5, borderColor: budgetLibre ? colors.primary : colors.border, borderRadius: rayon.field, backgroundColor: colors.surface, paddingHorizontal: sp[4] }}>
          <TextInput
            value={budgetLibre ? String(valeur.max_rent) : ""}
            onChangeText={(v) => {
              const chiffres = v.replace(/\D/g, "").slice(0, 7);
              maj({ max_rent: chiffres ? Number(chiffres) : null });
            }}
            keyboardType="number-pad"
            placeholder="Autre montant"
            placeholderTextColor={colors.textMuted}
            accessibilityLabel="Budget maximum en francs CFA"
            style={{ flex: 1, fontSize: 16, fontWeight: "600", color: colors.night, paddingVertical: 0 }}
          />
          <Text variante="corpsGras" muted>F / mois</Text>
        </View>
      </View>

      <Bloc titre="Distance de l'UP">
        {DISTANCES.map((d) => (
          <Chip key={d} titre={d >= 1000 ? `≤ ${d / 1000} km` : `≤ ${d} m`} actif={valeur.max_distance_m === d} onPress={() => maj({ max_distance_m: valeur.max_distance_m === d ? null : d })} />
        ))}
      </Bloc>

      <Bloc titre="Équipements">
        <Chip titre="Douche interne" actif={valeur.private_bathroom_required} onPress={() => maj({ private_bathroom_required: !valeur.private_bathroom_required })} />
      </Bloc>
    </View>
  );
}
