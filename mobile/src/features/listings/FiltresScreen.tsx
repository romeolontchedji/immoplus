import { useState } from "react";
import { Pressable, TextInput, View } from "react-native";
import { useRouter } from "expo-router";
import { X } from "lucide-react-native";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { ListeDeroulante, type Option } from "@/ui/components/ListeDeroulante";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { CIBLE_MIN, colors, rayon, sp } from "@/ui/theme/tokens";
import { t } from "@/i18n/fr";
import { francs } from "@/lib/format";
import { FILTRES_VIDES, LIBELLES_COMPTEUR, LIBELLES_CUISINE, LIBELLES_EAU, LIBELLES_TRI, useFiltres, type Filtres } from "./filtres";
import { useDistricts, useFil, useTypesChambre } from "./queries";

const BUDGETS = [15_000, 20_000, 25_000, 30_000, 40_000, 50_000, 75_000, 100_000] as const;
const DISTANCES = [500, 1000, 2000, 3000] as const;

const options = (libelles: Record<string, string>): Option[] => Object.entries(libelles).map(([valeur, libelle]) => ({ valeur, libelle }));
/** Une liste à choix unique : « [] » = tous (le premier élément de la liste du serveur sinon). */
const un = (v: string[] | undefined): string[] => (v?.length ? v.slice(0, 1) : []);

/**
 * Feuille de filtres (plan d'actions v3, A1 et A3) : des listes déroulantes au lieu de longues rangées de pastilles, et
 * chaque choix s'applique tout de suite (les résultats de l'onglet Recherche se mettent à jour derrière). Le bouton du bas
 * annonce le nombre réel de chambres et ferme la feuille.
 */
export function FiltresScreen() {
  const router = useRouter();
  const { filtres, definir } = useFiltres();
  const types = useTypesChambre();
  const districts = useDistricts();
  const resultats = useFil(filtres);
  const [budgetLibre, setBudgetLibre] = useState(
    filtres.rent_max !== undefined && !BUDGETS.includes(filtres.rent_max as (typeof BUDGETS)[number]) ? String(filtres.rent_max) : "",
  );

  const maj = (p: Partial<Filtres>) => definir({ ...filtres, ...p });
  const premierePage = resultats.data?.pages[0];
  const n = premierePage?.items.length ?? 0;
  const titreBouton = !premierePage
    ? "Voir les chambres"
    : n === 0
      ? premierePage.voisins?.items.length
        ? "Voir les quartiers voisins"
        : "Aucune chambre pour ces critères"
      : premierePage.next_cursor
        ? `Voir plus de ${n} chambres`
        : `Voir ${n} chambre${n > 1 ? "s" : ""}`;

  return (
    <Screen scroll footer={<Button titre={titreBouton} chargement={resultats.isFetching && !premierePage} onPress={() => router.back()} />}>
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
            definir({ ...FILTRES_VIDES, q: filtres.q });
            setBudgetLibre("");
          }}
          style={{ minHeight: CIBLE_MIN, justifyContent: "center", paddingLeft: sp[4] }}
        >
          <Text variante="lien" style={{ fontWeight: "700" }}>Réinitialiser</Text>
        </Pressable>
      </View>

      <View style={{ gap: sp[5], paddingBottom: sp[4] }}>
        <ListeDeroulante
          label="Quartier"
          placeholder="Tous les quartiers"
          options={(districts.data ?? []).map((d) => ({ valeur: d.slug, libelle: d.name }))}
          valeurs={un(filtres.district)}
          onChange={(v) => maj({ district: v })}
        />
        <ListeDeroulante
          label="Type de chambre"
          placeholder="Tous les types"
          options={types.map((x) => ({ valeur: x.slug, libelle: x.label }))}
          valeurs={un(filtres.type)}
          onChange={(v) => maj({ type: v })}
        />
        <ListeDeroulante
          label="Budget maximum"
          placeholder="Tous les budgets"
          options={BUDGETS.map((b) => ({ valeur: String(b), libelle: `Jusqu'à ${francs(b)}` }))}
          valeurs={filtres.rent_max !== undefined && budgetLibre === "" ? [String(filtres.rent_max)] : []}
          onChange={(v) => {
            setBudgetLibre("");
            maj({ rent_max: v.length ? Number(v[0]) : undefined });
          }}
          pied={
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
                accessibilityLabel="Autre budget maximum en francs CFA"
                style={{ flex: 1, fontSize: 16, fontWeight: "600", color: colors.night, paddingVertical: 0 }}
              />
              <Text variante="corpsGras" muted>F / mois</Text>
            </View>
          }
        />
        <View style={{ flexDirection: "row", gap: sp[3] }}>
          <View style={{ flex: 1 }}>
            <ListeDeroulante label="Électricité" placeholder="Peu importe" options={options(LIBELLES_COMPTEUR)} valeurs={un(filtres.meter)} onChange={(v) => maj({ meter: v })} />
          </View>
          <View style={{ flex: 1 }}>
            <ListeDeroulante label="Eau" placeholder="Peu importe" options={options(LIBELLES_EAU)} valeurs={un(filtres.water)} onChange={(v) => maj({ water: v })} />
          </View>
        </View>
        <View style={{ flexDirection: "row", gap: sp[3] }}>
          <View style={{ flex: 1 }}>
            <ListeDeroulante label="Cuisine" placeholder="Peu importe" options={options(LIBELLES_CUISINE)} valeurs={un(filtres.kitchen)} onChange={(v) => maj({ kitchen: v })} />
          </View>
          <View style={{ flex: 1 }}>
            <ListeDeroulante
              label="Distance de l'UP"
              placeholder="Peu importe"
              options={DISTANCES.map((d) => ({ valeur: String(d), libelle: d < 1000 ? `≤ ${d} m` : `≤ ${d / 1000} km` }))}
              valeurs={filtres.max_distance_m !== undefined ? [String(filtres.max_distance_m)] : []}
              onChange={(v) => maj({ max_distance_m: v.length ? Number(v[0]) : undefined })}
            />
          </View>
        </View>
        <ListeDeroulante
          label="Trier par"
          options={options(LIBELLES_TRI)}
          valeurs={[filtres.sort]}
          onChange={(v) => maj({ sort: (v[0] ?? "recent") as Filtres["sort"] })}
        />
        <View style={{ gap: sp[2] }}>
          <Text variante="label" muted>Indispensable</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
            <Chip titre="Douche interne" actif={!!filtres.bathroom} onPress={() => maj({ bathroom: filtres.bathroom ? undefined : true })} />
            <Chip titre="Cour clôturée" actif={!!filtres.fenced} onPress={() => maj({ fenced: filtres.fenced ? undefined : true })} />
          </View>
        </View>
      </View>
    </Screen>
  );
}
