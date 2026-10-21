import { useState } from "react";
import { TextInput, View } from "react-native";
import { francs } from "@/lib/format";
import { ListeDeroulante } from "@/ui/components/ListeDeroulante";
import { Text } from "@/ui/components/Text";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { LIBELLES_COMPTEUR, LIBELLES_CUISINE, LIBELLES_EAU, type Filtres } from "@/features/listings/filtres";
import { libelleType, TYPES_OFFICIELS, useDistricts, useTypesChambre, type TypeChambre } from "@/features/listings/queries";
import { type Alerte, type AlerteEntree, useOptionsAlerte } from "./queries";

const BUDGETS_REPLI = [10_000, 15_000, 20_000, 25_000, 30_000, 40_000, 50_000];
const AUTRE = "autre";
const DISTANCES = [500, 1000, 2000, 5000] as const;
const INDISPENSABLES = { douche: "Douche et WC internes", cloture: "Cour clôturée" };
const CUISINES = { private: LIBELLES_CUISINE.private ?? "Cuisine interne", shared: LIBELLES_CUISINE.shared ?? "Cuisine commune" };
const versOptions = (libelles: Record<string, string>) => Object.entries(libelles).map(([valeur, libelle]) => ({ valeur, libelle }));

/** Critères d'une alerte, au format de l'API (`AlerteIn`). */
export type Criteres = {
  district_ids: string[];
  room_types: string[];
  max_rent: number | null;
  private_bathroom_required: boolean;
  max_distance_m: number | null;
  water_sources: string[];
  electricity_meters: string[];
  kitchens: string[];
  fenced_required: boolean;
};

export const CRITERES_VIDES: Criteres = {
  district_ids: [], room_types: [], max_rent: null, private_bathroom_required: false, max_distance_m: null,
  water_sources: [], electricity_meters: [], kitchens: [], fenced_required: false,
};

/** Il faut au moins une option pour créer une alerte (demande du 2026-10-20). */
export const aUnCritere = (c: Criteres): boolean =>
  c.district_ids.length > 0 || c.room_types.length > 0 || c.max_rent !== null || c.max_distance_m !== null ||
  c.private_bathroom_required || c.fenced_required || c.water_sources.length > 0 || c.electricity_meters.length > 0 ||
  c.kitchens.length > 0;

export const criteresDe = (a: Alerte): Criteres => ({
  district_ids: a.district_ids ?? [],
  room_types: a.room_types ?? [],
  max_rent: a.max_rent ?? null,
  private_bathroom_required: !!a.private_bathroom_required,
  max_distance_m: a.max_distance_m ?? null,
  water_sources: a.water_sources ?? [],
  electricity_meters: a.electricity_meters ?? [],
  kitchens: a.kitchens ?? [],
  fenced_required: !!a.fenced_required,
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
    water_sources: f.water ?? [],
    electricity_meters: f.meter ?? [],
    kitchens: (f.kitchen ?? []).filter((k) => k !== "none"),
    fenced_required: !!f.fenced,
  };
}

/** Résumé lisible : « Banikanni, Titirou · Entrée-coucher · ≤ 15 000 F ». */
export function resumeCriteres(c: Criteres, noms: Record<string, string>, typesConnus: TypeChambre[] = TYPES_OFFICIELS): { titre: string; details: string } {
  const lieux = c.district_ids.map((id) => noms[id]).filter(Boolean).join(", ");
  const types = c.room_types.map((tp) => libelleType(typesConnus, tp)).join(", ");
  const details = [
    c.max_rent ? `≤ ${francs(c.max_rent)}` : null,
    c.max_distance_m ? `≤ ${c.max_distance_m} m de l'UP` : null,
    ...c.water_sources.map((e) => LIBELLES_EAU[e] ?? e),
    ...c.electricity_meters.map((e) => LIBELLES_COMPTEUR[e] ?? e),
    ...c.kitchens.map((e) => LIBELLES_CUISINE[e] ?? e),
    c.private_bathroom_required ? "Douche interne" : null,
    c.fenced_required ? "Cour clôturée" : null,
  ].filter(Boolean).join(" · ");
  return { titre: [lieux, types].filter(Boolean).join(" · ") || "Toutes les chambres", details };
}

/**
 * Éditeur des critères d'alerte : chaque critère est une liste déroulante, à choix multiples sauf le budget et la
 * distance (plan v2, M5, et demande du 2026-10-20). Quartiers les plus demandés d'abord ; « Autre montant » ouvre
 * un champ pour un budget libre. Équipements : eau, électricité, cuisine, douche interne, cour clôturée.
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

      <ListeDeroulante
        label="Types de chambre"
        placeholder="Tous les types"
        multiple
        options={types.map(({ slug, label }) => ({ valeur: slug, libelle: label }))}
        valeurs={valeur.room_types}
        onChange={(v) => maj({ room_types: v })}
      />

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

      <ListeDeroulante
        label="Distance de l'UP"
        placeholder="Peu importe"
        options={DISTANCES.map((d) => ({ valeur: String(d), libelle: d >= 1000 ? `À ${d / 1000} km au plus` : `À ${d} m au plus` }))}
        valeurs={valeur.max_distance_m !== null ? [String(valeur.max_distance_m)] : []}
        onChange={([v]) => maj({ max_distance_m: v ? Number(v) : null })}
      />
      <ListeDeroulante label="Eau" placeholder="Peu importe" multiple options={versOptions(LIBELLES_EAU)} valeurs={valeur.water_sources} onChange={(v) => maj({ water_sources: v })} />
      <ListeDeroulante label="Électricité" placeholder="Peu importe" multiple options={versOptions(LIBELLES_COMPTEUR)} valeurs={valeur.electricity_meters} onChange={(v) => maj({ electricity_meters: v })} />
      <ListeDeroulante label="Cuisine" placeholder="Peu importe" multiple options={versOptions(CUISINES)} valeurs={valeur.kitchens} onChange={(v) => maj({ kitchens: v })} />
      <ListeDeroulante
        label="Indispensables"
        placeholder="Rien d'obligatoire"
        multiple
        options={versOptions(INDISPENSABLES)}
        valeurs={[valeur.private_bathroom_required ? "douche" : "", valeur.fenced_required ? "cloture" : ""].filter(Boolean)}
        onChange={(v) => maj({ private_bathroom_required: v.includes("douche"), fenced_required: v.includes("cloture") })}
      />
    </View>
  );
}
