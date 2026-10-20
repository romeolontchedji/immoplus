import { useState } from "react";
import { useRouter } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { qk } from "@/api/keys";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { TextField } from "@/ui/components/TextField";
import { CHAMPS_CREATION, champsManquants, useBrouillon } from "./brouillon";
import { EntetePublication } from "./EntetePublication";

/** Étape de l'assistant où se saisit chaque champ obligatoire. */
const ETAPE_DU_CHAMP: Partial<Record<(typeof CHAMPS_CREATION)[number], string>> = {
  district: "localisation", landmark_text: "localisation", address_private: "localisation",
  water_source: "equipements", electricity_meter: "equipements", kitchen: "equipements", has_private_bathroom: "equipements",
  is_fenced: "equipements",
};

/**
 * Étape « Autres détails » (plan v3, C1) : un texte simple, sans mise en forme, pour ce que les champs précédents ne
 * disent pas (règles de la maison, voisinage, marché proche…). Crée l'annonce côté serveur (brouillon) ou la met à jour.
 */
export function DescriptionStep() {
  const { c } = useTheme();
  const router = useRouter();
  const { brouillon, maj } = useBrouillon();
  const qc = useQueryClient();
  const [details, setDetails] = useState(brouillon.description_md ?? "");

  const creer = useMutation({
    mutationFn: async (corps: Record<string, unknown>) => unwrap(api.POST("/v1/pro/listings", { body: corps as never })),
    onSuccess: (data) => {
      maj({ serveurId: data.id });
      void qc.invalidateQueries({ queryKey: qk.pro.annonces });
    },
  });
  const modifier = useMutation({
    mutationFn: async (corps: Record<string, unknown>) =>
      unwrap(api.PATCH("/v1/pro/listings/{annonce_id}", { params: { path: { annonce_id: brouillon.serveurId as string } }, body: corps as never })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.pro.annonce(brouillon.serveurId ?? "") }),
  });
  const erreur = creer.error ?? modifier.error;

  const suivant = () => {
    const brouillonMaj = { ...brouillon, description_md: details };
    maj({ description_md: details });
    const manques = champsManquants(brouillonMaj);
    if (brouillonMaj.serveurId) {
      modifier.mutate(
        {
          description_md: details, has_private_bathroom: !!brouillonMaj.has_private_bathroom, is_fenced: !!brouillonMaj.is_fenced,
          water_source: brouillonMaj.water_source, electricity_meter: brouillonMaj.electricity_meter,
          kitchen: brouillonMaj.kitchen ?? "", rent_negotiable: !!brouillonMaj.rent_negotiable,
        },
        { onSuccess: () => router.push("/pro/nouvelle-annonce/medias" as never) },
      );
      return;
    }
    if (manques.length) {
      // Un champ obligatoire manque (brouillon ancien ou étape sautée) : retour à l'étape concernée.
      router.push(`/pro/nouvelle-annonce/${ETAPE_DU_CHAMP[manques[0]!] ?? "infos"}` as never);
      return;
    }
    const corps: Record<string, unknown> = { rent_negotiable: !!brouillonMaj.rent_negotiable };
    for (const cle of CHAMPS_CREATION) corps[cle] = brouillonMaj[cle];
    if (brouillonMaj.latitude && brouillonMaj.longitude) Object.assign(corps, { latitude: brouillonMaj.latitude, longitude: brouillonMaj.longitude });
    if (details.trim()) corps.description_md = details;
    creer.mutate(corps, { onSuccess: () => router.push("/pro/nouvelle-annonce/medias" as never) });
  };

  return (
    <Screen scroll footer={<Button titre="Enregistrer le brouillon et continuer" chargement={creer.isPending || modifier.isPending} onPress={suivant} />}>
      <EntetePublication etape={4} total={6} />

      <Text variante="titre" style={{ marginTop: sp[2] }}>Autres détails</Text>
      <Text muted>Ce que les étapes précédentes ne disent pas. Facultatif, en texte simple.</Text>

      <TextField
        label="Autres détails"
        value={details}
        onChangeText={setDetails}
        multiline
        maxLength={4000}
        placeholder={"Ex. Chambre au calme, à 5 minutes du marché Arzèkè.\nPas d'animaux. Visite possible le soir."}
        aide="Les numéros, e-mails et liens sont refusés : les échanges passent par la messagerie Immo+."
      />

      {erreur ? (
        <Text variante="legende" couleur={c.danger} accessibilityLiveRegion="polite">
          {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.erreurs.network}
        </Text>
      ) : null}
    </Screen>
  );
}
