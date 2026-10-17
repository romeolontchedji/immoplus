import { useState } from "react";
import { TextInput, View } from "react-native";
import { francs } from "@/lib/format";
import { t } from "@/i18n/fr";
import { Chip } from "@/ui/components/Chip";
import { ListeDeroulante } from "@/ui/components/ListeDeroulante";
import { Text } from "@/ui/components/Text";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import type { Filtres } from "@/features/listings/filtres";
import { libelleType, TYPES_OFFICIELS, useDistricts, useTypesChambre, type TypeChambre } from "@/features/listings/queries";
import { type Alerte, type AlerteEntree, useOptionsAlerte } from "./queries";

const BUDGETS_REPLI = [10_000, 15_000, 20_000, 25_000, 30_000, 40_000, 50_000];
const AUTRE = "autre";
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
export function resumeCriteres(c: Criteres, noms: Record<string, string>, typesConnus: TypeChambre[] = TYPES_OFFICIELS): { titre: string; details: string } {
  const lieux = c.district_ids.map((id) => noms[id]).filter(Boolean).join(", ");
  const types = c.room_types.map((tp) => libelleType(typesConnus, tp)).join(", ");
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

/**
 * Éditeur des critères d'alerte (plan v2, M5) : quartiers en liste déroulante multiple, les plus demandés d'abord ;
 * budget en liste déroulante de montants fréquents, avec « Autre montant » qui fait apparaître un champ.
 */
export function EditeurCriteres({ valeur, onChange }: { valeur: Criteres; onChange: (c: Criteres) => void }) {
  const options = useOptionsAlerte();
  const districts = useDistricts();
  const types = useTypesChambre();
  const maj = (p: Partial<Criteres>) => onChange({ ...valeur, ...p });
  const budgets = options.data?.budgets?.length ? options.data.budgets : BUDGETS_REPLI;
  const [autreMontant, setAutreMontant] = useState(valeur.max_rent !== null && !budgets.includes(valeur.max_rent));

  const quartiers = options.data?.districts.map((q) => ({
    valeur: q.id,
    libelle: q.name,
    aide: [q.alerts ? `${q.alerts} alerte${q.alerts > 1 ? "s" : ""}` : null, q.listings ? `${q.listings} chambre${q.listings > 1 ? "s" : ""} en ligne` : null].filter(Boolean).join(" · ") || undefined,
  })) ?? (districts.data ?? []).map((d) => ({ valeur: d.id, libelle: d.name }));

  const choixBudget = autreMontant ? [AUTRE] : valeur.max_rent !== null ? [String(valeur.max_rent)] : [];

  return (
    <View style={{ gap: sp[5] }}>
      <ListeDeroulante
        label="Quartiers"
        placeholder="Tous les quartiers"
        multiple
        recherche
        options={quartiers}
        valeurs={valeur.district_ids}
        onChange={(ids) => maj({ district_ids: ids })}
      />

      <Bloc titre="Type">
        {types.map(({ slug, label }) => (
          <Chip key={slug} titre={label} actif={valeur.room_types.includes(slug)} onPress={() => maj({ room_types: basculer(valeur.room_types, slug) })} />
        ))}
      </Bloc>

      <View style={{ gap: sp[2] }}>
        <ListeDeroulante
          label="Budget maximum"
          placeholder="Pas de limite"
          options={[...budgets.map((b) => ({ valeur: String(b), libelle: `Jusqu'à ${francs(b)} / mois` })), { valeur: AUTRE, libelle: "Autre montant…" }]}
          valeurs={choixBudget}
          onChange={([v]) => {
            if (v === AUTRE) {
              setAutreMontant(true);
              return;
            }
            setAutreMontant(false);
            maj({ max_rent: v ? Number(v) : null });
          }}
        />
        {autreMontant ? (
          <View style={{ flexDirection: "row", alignItems: "center", minHeight: 52, borderWidth: 1.5, borderColor: colors.primary, borderRadius: rayon.field, backgroundColor: colors.surface, paddingHorizontal: sp[4] }}>
            <TextInput
              autoFocus
              value={valeur.max_rent !== null ? String(valeur.max_rent) : ""}
              onChangeText={(v) => {
                const chiffres = v.replace(/\D/g, "").slice(0, 7);
                maj({ max_rent: chiffres ? Number(chiffres) : null });
              }}
              keyboardType="number-pad"
              placeholder="Ton montant"
              placeholderTextColor={colors.textMuted}
              accessibilityLabel="Budget maximum en francs CFA"
              style={{ flex: 1, fontSize: 16, fontWeight: "600", color: colors.night, paddingVertical: 0 }}
            />
            <Text variante="corpsGras" muted>F / mois</Text>
          </View>
        ) : null}
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
