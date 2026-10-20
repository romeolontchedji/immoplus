import { useState, type ReactNode } from "react";
import { View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { useDistricts } from "@/features/listings/queries";
import { colors, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { ListeDeroulante } from "@/ui/components/ListeDeroulante";
import { LIBELLES_COMPTEUR, LIBELLES_CUISINE, LIBELLES_EAU } from "@/features/listings/filtres";
import { type AnnoncePro, type ModificationAnnonce, useAnnoncePro, useModifierAnnonce, useTypesChambrePro } from "./queries";

const options = (libelles: Record<string, string>) => Object.entries(libelles).map(([valeur, libelle]) => ({ valeur, libelle }));

function Section({ titre, children }: { titre: string; children: ReactNode }) {
  return (
    <View style={{ gap: sp[2] }}>
      <Text variante="label" muted>{titre}</Text>
      {children}
    </View>
  );
}

const entier = (v: string) => (v.trim() === "" ? undefined : Number(v.replace(/\D/g, "")));

type Valeurs = {
  title: string; room_type: string; district: string; landmark_text: string; address_private: string;
  rent_amount: string; deposit_months: string; advance_months: string; agent_fee_amount: string; available_from: string;
  has_private_bathroom: boolean; is_fenced: boolean; water_source: string; electricity_meter: string; kitchen: string;
  rent_negotiable: boolean; description_md: string;
};

const depuis = (a: AnnoncePro): Valeurs => ({
  title: a.title, room_type: a.room_type, district: a.district, landmark_text: a.landmark_text, address_private: a.address_private,
  rent_amount: String(a.rent_amount), deposit_months: String(a.deposit_months), advance_months: String(a.advance_months),
  agent_fee_amount: String(a.agent_fee_amount), available_from: a.available_from, has_private_bathroom: a.has_private_bathroom,
  is_fenced: a.is_fenced, water_source: a.water_source, electricity_meter: a.electricity_meter, kitchen: a.kitchen,
  rent_negotiable: a.rent_negotiable, description_md: a.description_md,
});

/** Seuls les champs modifiés partent au serveur (PATCH) : une annonce en ligne n'est pas réécrite inutilement. */
function differences(avant: Valeurs, apres: Valeurs): ModificationAnnonce {
  const corps: Record<string, unknown> = {};
  for (const cle of Object.keys(apres) as (keyof Valeurs)[]) {
    if (apres[cle] === avant[cle]) continue;
    corps[cle] = ["rent_amount", "deposit_months", "advance_months", "agent_fee_amount"].includes(cle) ? entier(String(apres[cle])) : apres[cle];
  }
  return corps as ModificationAnnonce;
}

function Formulaire({ annonce }: { annonce: AnnoncePro }) {
  const router = useRouter();
  const initial = depuis(annonce);
  const [v, setV] = useState<Valeurs>(initial);
  const maj = (m: Partial<Valeurs>) => setV((x) => ({ ...x, ...m }));
  const types = useTypesChambrePro();
  const quartiers = useDistricts();
  const modifier = useModifierAnnonce(annonce.id);
  const corps = differences(initial, v);
  const rien = Object.keys(corps).length === 0;
  const champsErreur = isApiError(modifier.error) ? modifier.error.fields ?? {} : {};
  const erreur = (cle: string) => champsErreur[cle]?.[0];

  return (
    <>
      <TextField label="Titre" value={v.title} onChangeText={(x) => maj({ title: x })} maxLength={120} erreur={erreur("title")} />

      <ListeDeroulante label="Type de chambre" options={(types.data ?? []).map((tp) => ({ valeur: tp.slug, libelle: tp.label }))} valeurs={[v.room_type]} onChange={(x) => x[0] && maj({ room_type: x[0] })} />

      <View style={{ gap: sp[1] }}>
        <ListeDeroulante label="Quartier" options={(quartiers.data ?? []).map((q) => ({ valeur: q.id, libelle: q.name }))} valeurs={[v.district]} onChange={(x) => x[0] && maj({ district: x[0] })} />
        {v.district !== initial.district ? <Text variante="legende" muted>La distance à l’UP sera recalculée depuis le centre du nouveau quartier.</Text> : null}
      </View>
      <TextField label="Repère (visible par les étudiants)" value={v.landmark_text} onChangeText={(x) => maj({ landmark_text: x })} erreur={erreur("landmark_text")} />
      <TextField label="Adresse précise (confidentielle)" value={v.address_private} onChangeText={(x) => maj({ address_private: x })} erreur={erreur("address_private")} />

      <View style={{ flexDirection: "row", gap: sp[3] }}>
        <View style={{ flex: 1 }}><TextField label="Loyer / mois (F)" value={v.rent_amount} onChangeText={(x) => maj({ rent_amount: x })} keyboardType="number-pad" erreur={erreur("rent_amount")} /></View>
        <View style={{ flex: 1 }}><TextField label="Frais de démarcheur (F)" value={v.agent_fee_amount} onChangeText={(x) => maj({ agent_fee_amount: x })} keyboardType="number-pad" /></View>
      </View>
      <View style={{ flexDirection: "row", gap: sp[3] }}>
        <View style={{ flex: 1 }}><TextField label="Caution (mois)" value={v.deposit_months} onChangeText={(x) => maj({ deposit_months: x })} keyboardType="number-pad" erreur={erreur("deposit_months")} /></View>
        <View style={{ flex: 1 }}><TextField label="Avance (mois)" value={v.advance_months} onChangeText={(x) => maj({ advance_months: x })} keyboardType="number-pad" erreur={erreur("advance_months")} /></View>
      </View>
      <SwitchRow titre="Prix à débattre" aide="La fiche affichera « à débattre » à côté du loyer." valeur={v.rent_negotiable} onChange={(x) => maj({ rent_negotiable: x })} />
      <TextField label="Disponible à partir du (AAAA-MM-JJ)" value={v.available_from} onChangeText={(x) => maj({ available_from: x })} erreur={erreur("available_from")} />

      <Section titre="Équipements">
        <SwitchRow titre="Douche interne" valeur={v.has_private_bathroom} onChange={(x) => maj({ has_private_bathroom: x })} />
        <SwitchRow titre="Cour clôturée" valeur={v.is_fenced} onChange={(x) => maj({ is_fenced: x })} />
        <ListeDeroulante label="Électricité" options={options(LIBELLES_COMPTEUR)} valeurs={[v.electricity_meter]} onChange={(x) => x[0] && maj({ electricity_meter: x[0] })} />
        <ListeDeroulante label="Eau" options={options(LIBELLES_EAU)} valeurs={[v.water_source]} onChange={(x) => x[0] && maj({ water_source: x[0] })} />
        <ListeDeroulante label="Cuisine" placeholder="Choisis" options={options(LIBELLES_CUISINE)} valeurs={v.kitchen ? [v.kitchen] : []} onChange={(x) => maj({ kitchen: x[0] ?? "" })} />
      </Section>

      <TextField label="Autres détails" value={v.description_md} onChangeText={(x) => maj({ description_md: x })} multiline maxLength={4000} aide="Texte simple : règles de la maison, voisinage, marché proche…" erreur={erreur("description_md")} />

      {modifier.error ? (
        <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
          {isApiError(modifier.error) ? messageErreur(modifier.error.code, modifier.error.message) : t.erreurs.network}
        </Text>
      ) : null}
      <Button titre={rien ? "Aucune modification" : "Enregistrer"} disabled={rien} chargement={modifier.isPending} onPress={() => modifier.mutate(corps, { onSuccess: () => router.back() })} />
    </>
  );
}

/** Modifier une annonce existante (plan v2, MM6) : formulaire unique, seuls les champs changés sont envoyés. */
export function AnnonceModifierScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const requete = useAnnoncePro(id);
  return (
    <Screen scroll>
      <QueryState query={requete}>{(a) => <Formulaire key={a.updated_at} annonce={a} />}</QueryState>
    </Screen>
  );
}
