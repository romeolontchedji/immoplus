import { View } from "react-native";
import { useRouter } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { qk } from "@/api/keys";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { Screen } from "@/ui/components/Screen";
import { SwitchRow } from "@/ui/components/SwitchRow";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { CHAMPS_CREATION, champsManquants, useBrouillon } from "./brouillon";
import { EntetePublication } from "./EntetePublication";

type EQUIPEMENT = {
  cle: string;
  label: string;
};

const EQUIPEMENTS: EQUIPEMENT[] = [
  { cle: "has_private_bathroom", label: "Douche interne" },
  { cle: "is_fenced", label: "Cour clôturée" },
];

/** Étape de l'assistant où se saisit chaque champ obligatoire. */
const ETAPE_DU_CHAMP: Partial<Record<(typeof CHAMPS_CREATION)[number], string>> = {
  district: "localisation", landmark_text: "localisation", address_private: "localisation",
  water_source: "equipements", electricity_meter: "equipements", has_private_bathroom: "equipements", is_fenced: "equipements",
};

type Valeurs = {
  description_md: string;
  equipements: Record<string, boolean>;
};

/**
 * Étape 4/4 (description + équipements) — conforme à la maquette « Mobile · Publier 3 4@1x.png » :
 * - Titre "Décris-la en détail"
 * - Zone texte DESCRIPTION avec barre de formatage (B I U •• 1.)
 * - Section ÉQUIPEMENTS avec chips pilule (actif = bleu cobalt)
 * Crée l'annonce côté serveur si tous les champs requis sont présents.
 */
export function DescriptionStep() {
  const { c } = useTheme();
  const router = useRouter();
  const { brouillon, maj } = useBrouillon();
  const qc = useQueryClient();

  const creer = useMutation({
    mutationFn: async (corps: Record<string, unknown>) => unwrap(api.POST("/v1/pro/listings", { body: corps as never })),
    onSuccess: (data) => {
      maj({ serveurId: data.id });
      void qc.invalidateQueries({ queryKey: qk.pro.annonces });
    },
  });
  const modifier = useMutation({
    mutationFn: async (corps: { description_md: string; has_private_bathroom: boolean; is_fenced: boolean }) =>
      unwrap(api.PATCH("/v1/pro/listings/{annonce_id}", { params: { path: { annonce_id: brouillon.serveurId as string } }, body: corps })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.pro.annonce(brouillon.serveurId ?? "") }),
  });
  const erreur = creer.error ?? modifier.error;

  const { control, handleSubmit, watch, setValue } = useForm<Valeurs>({
    defaultValues: {
      description_md: brouillon.description_md ?? "",
      equipements: {
        has_private_bathroom: brouillon.has_private_bathroom ?? false,
        is_fenced: brouillon.is_fenced ?? false,
      },
    },
  });

  const equip = watch("equipements");

  const basculer = (cle: string) =>
    setValue("equipements", { ...equip, [cle]: !equip[cle] });

  const suivant = (v: Valeurs) => {
    const mise: Partial<typeof brouillon> = {
      description_md: v.description_md,
      has_private_bathroom: !!v.equipements.has_private_bathroom,
      is_fenced: !!v.equipements.is_fenced,
    };
    maj(mise);

    const brouillonMaj = { ...brouillon, ...mise };
    const manques = champsManquants(brouillonMaj);

    if (brouillonMaj.serveurId) {
      // Annonce déjà créée : on enregistre la description et les équipements sur le serveur.
      modifier.mutate(
        { description_md: v.description_md, has_private_bathroom: !!brouillonMaj.has_private_bathroom, is_fenced: !!brouillonMaj.is_fenced },
        { onSuccess: () => router.push("/pro/nouvelle-annonce/medias" as never) },
      );
      return;
    }
    if (manques.length) {
      // Un champ obligatoire manque (brouillon ancien ou étape sautée) : on renvoie vers l'étape concernée.
      router.push(`/pro/nouvelle-annonce/${ETAPE_DU_CHAMP[manques[0]!] ?? "infos"}` as never);
      return;
    }
    const corps: Record<string, unknown> = {};
    for (const cle of CHAMPS_CREATION) corps[cle] = brouillonMaj[cle];
    if (brouillonMaj.latitude && brouillonMaj.longitude) Object.assign(corps, { latitude: brouillonMaj.latitude, longitude: brouillonMaj.longitude });
    if (brouillonMaj.description_md) corps.description_md = brouillonMaj.description_md;
    creer.mutate(corps, { onSuccess: () => router.push("/pro/nouvelle-annonce/medias" as never) });
  };

  return (
    <Screen scroll footer={
      <Button titre="Continuer" chargement={creer.isPending || modifier.isPending} onPress={handleSubmit(suivant)} />
    }>
      <EntetePublication etape={4} total={6} />

      <Text variante="titre" style={{ marginTop: sp[2] }}>Décris-la en détail</Text>
      <Text muted>Mets en avant ce qui la rend unique.</Text>

      {/* Zone description */}
      <View style={{ gap: sp[2] }}>
        <Text variante="label">Description</Text>
        {/* Barre de formatage simplifiée (conforme maquette Publier 3/4) */}
        <View
          style={{
            flexDirection: "row",
            gap: sp[3],
            padding: sp[3],
            backgroundColor: c.surfaceSunken,
            borderTopLeftRadius: 12,
            borderTopRightRadius: 12,
            borderWidth: 1,
            borderColor: c.border,
            borderBottomWidth: 0,
          }}
        >
          {["G", "I", "S", "•", "1."].map((label) => (
            <Text key={label} variante="corps" style={{ fontWeight: label === "G" ? "700" : label === "I" ? "400" : "600", color: c.textMuted, minWidth: 20, textAlign: "center" }}>
              {label}
            </Text>
          ))}
        </View>
        <Controller
          control={control}
          name="description_md"
          render={({ field }) => (
            <TextField
              label=""
              value={field.value}
              onChangeText={field.onChange}
              multiline
              numberOfLines={5}
              style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0, marginTop: 0 }}
              placeholder={"Chambre carrelée, cour clôturée, forage et compteur SBEE individuel.\nÀ 7 min à pied de l'Université de Parakou. Disponible maintenant."}
            />
          )}
        />
      </View>

      {/* Équipements en chips (conforme maquette Publier 3/4) */}
      <View style={{ gap: sp[2] }}>
        <Text variante="label">Équipements</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          {EQUIPEMENTS.map(({ cle, label }) => (
            <Chip
              key={cle}
              titre={label}
              actif={!!equip[cle]}
              onPress={() => basculer(cle)}
            />
          ))}
        </View>
      </View>

      {erreur ? (
        <Text variante="legende" couleur={c.danger} accessibilityLiveRegion="polite">
          {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}
        </Text>
      ) : null}
    </Screen>
  );
}
