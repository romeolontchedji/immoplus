import { useState, type ReactNode } from "react";
import { Pressable, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { X } from "lucide-react-native";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { CIBLE_MIN, colors, rayon, sp } from "@/ui/theme/tokens";
import { t } from "@/i18n/fr";
import { francs } from "@/lib/format";
import { FILTRES_VIDES, LIBELLES_EAU, LIBELLES_TRI, type Filtres } from "./filtres";
import { useFiltres } from "./filtres";
import { useDistricts, useFil, useTypesChambre } from "./queries";

const BUDGETS = [10_000, 15_000, 20_000, 30_000] as const;
const DISTANCES = [
  { val: 500, label: "≤ 500 m" },
  { val: 1000, label: "≤ 1 km" },
  { val: 2000, label: "≤ 2 km" },
] as const;

const basculerDans = (liste: string[], v: string) => (liste.includes(v) ? liste.filter((x) => x !== v) : [...liste, v]);

function Section({ titre, children }: { titre: string; children: ReactNode }) {
  return (
    <View style={{ gap: sp[3] }}>
      <Text variante="label" muted>{titre}</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>{children}</View>
    </View>
  );
}

/**
 * Feuille de filtres (EF-REC-05, maquette Mobile · Filtres). Les choix restent en brouillon jusqu'au bouton du bas, qui
 * annonce le nombre réel de chambres trouvées avec ces critères. Seuls les critères acceptés par GET /v1/listings sont
 * proposés (pas de « Gérant vérifié » ni « Avec vidéo » : aucun paramètre serveur, voir docs/design/ECARTS.md).
 */
export function FiltresScreen() {
  const router = useRouter();
  const { filtres, definir } = useFiltres();
  const types = useTypesChambre();
  const [brouillon, setBrouillon] = useState<Filtres>({ ...FILTRES_VIDES, ...filtres });
  const [budgetLibre, setBudgetLibre] = useState(
    filtres.rent_max !== undefined && !BUDGETS.includes(filtres.rent_max as (typeof BUDGETS)[number]) ? String(filtres.rent_max) : "",
  );
  const districts = useDistricts();
  const apercu = useFil(brouillon);

  const maj = (p: Partial<Filtres>) => setBrouillon((b) => ({ ...b, ...p }));
  const premierePage = apercu.data?.pages[0];
  const n = premierePage?.items.length ?? 0;
  const titreBouton = !premierePage
    ? "Voir les chambres"
    : n === 0
      ? "Aucune chambre, élargis tes critères"
      : premierePage.next_cursor
        ? `Voir plus de ${n} chambres`
        : `Voir ${n} chambre${n > 1 ? "s" : ""}`;

  return (
    <Screen
      scroll
      footer={
        <Button
          titre={titreBouton}
          chargement={apercu.isFetching && !premierePage}
          disabled={premierePage !== undefined && n === 0}
          onPress={() => {
            definir(brouillon);
            router.back();
          }}
        />
      }
    >
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t.commun.fermer}
            onPress={() => router.back()}
            style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center" }}
          >
            <X size={18} color={colors.night} />
          </Pressable>
          <Text variante="titreSection">Filtres</Text>
        </View>
        <Pressable
          accessibilityRole="button"
          onPress={() => {
            setBrouillon({ ...FILTRES_VIDES, q: brouillon.q });
            setBudgetLibre("");
          }}
          style={{ minHeight: CIBLE_MIN, justifyContent: "center", paddingLeft: sp[4] }}
        >
          <Text variante="lien" style={{ fontWeight: "700" }}>Réinitialiser</Text>
        </Pressable>
      </View>

      <View style={{ gap: sp[6], paddingBottom: sp[4] }}>
        <Section titre="Trier par">
          {(Object.keys(LIBELLES_TRI) as Filtres["sort"][]).map((tri) => (
            <Chip key={tri} titre={LIBELLES_TRI[tri]} actif={brouillon.sort === tri} onPress={() => maj({ sort: tri })} />
          ))}
        </Section>

        <View style={{ gap: sp[3] }}>
          <Text variante="label" muted>Quartier</Text>
          <QueryState query={districts}>
            {(liste) => (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
                {liste.map((d) => (
                  <Chip key={d.slug} titre={d.name} actif={brouillon.district.includes(d.slug)} onPress={() => maj({ district: basculerDans(brouillon.district, d.slug) })} />
                ))}
              </View>
            )}
          </QueryState>
        </View>

        <View style={{ gap: sp[3] }}>
          <Text variante="label" muted>{brouillon.rent_max !== undefined ? `Budget max · ${francs(brouillon.rent_max)}` : "Budget max"}</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
            {BUDGETS.map((b) => (
              <Chip
                key={b}
                titre={`≤ ${francs(b)}`}
                actif={brouillon.rent_max === b && budgetLibre === ""}
                onPress={() => {
                  setBudgetLibre("");
                  maj({ rent_max: brouillon.rent_max === b ? undefined : b });
                }}
              />
            ))}
          </View>
          <View style={{ flexDirection: "row", alignItems: "center", minHeight: 52, borderWidth: 1.5, borderColor: budgetLibre ? colors.primary : colors.border, borderRadius: rayon.field, backgroundColor: colors.surface, paddingHorizontal: sp[4] }}>
            <TextInput
              value={budgetLibre}
              onChangeText={(v) => {
                const chiffres = v.replace(/\D/g, "").slice(0, 7);
                setBudgetLibre(chiffres);
                maj({ rent_max: chiffres ? Number(chiffres) : undefined });
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

        <Section titre="Type">
          {types.map(({ slug, label }) => (
            <Chip key={slug} titre={label} actif={brouillon.type.includes(slug)} onPress={() => maj({ type: basculerDans(brouillon.type, slug) })} />
          ))}
        </Section>

        <Section titre="Distance de l'UP">
          {DISTANCES.map(({ val, label }) => (
            <Chip key={val} titre={label} actif={brouillon.max_distance_m === val} onPress={() => maj({ max_distance_m: brouillon.max_distance_m === val ? undefined : val })} />
          ))}
        </Section>

        <Section titre="Équipements">
          <Chip titre="Douche interne" actif={!!brouillon.bathroom} onPress={() => maj({ bathroom: brouillon.bathroom ? undefined : true })} />
          <Chip titre="Cour clôturée" actif={!!brouillon.fenced} onPress={() => maj({ fenced: brouillon.fenced ? undefined : true })} />
        </Section>

        <Section titre="Eau">
          {Object.entries(LIBELLES_EAU).map(([cle, libelle]) => (
            <Chip key={cle} titre={libelle} actif={brouillon.water.includes(cle)} onPress={() => maj({ water: basculerDans(brouillon.water, cle) })} />
          ))}
        </Section>
      </View>
    </Screen>
  );
}
