import { useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { colors } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { SkeletonListe } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { useFiltres } from "@/features/listings/filtres";
import { proposerNotifications } from "@/features/notifications/DemandeNotifications";
import { useDistricts } from "@/features/listings/queries";
import { criteresDe, criteresDepuisFiltres, EditeurCriteres, versCorps, type Criteres } from "./EditeurCriteres";
import { useAlertes, useCreerAlerte, useModifierAlerte } from "./queries";

/**
 * Création et modification d'une alerte (EF-ALR-01). /nouvelle-alerte part de la recherche en cours ;
 * /modifier-alerte/[id] préremplit l'alerte puis envoie un PATCH.
 */
export function AlerteFormScreen() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { filtres } = useFiltres();
  const districts = useDistricts();
  const alertes = useAlertes(!!id);

  // On attend les données de départ, puis le formulaire est monté une seule fois avec ses valeurs initiales.
  let initiales: Criteres | undefined;
  if (id) {
    const alerte = alertes.data?.find((a) => a.id === id);
    if (alerte) initiales = criteresDe(alerte);
  } else if (districts.data || districts.isError) {
    initiales = criteresDepuisFiltres(filtres, districts.data ?? []);
  }

  if (!initiales) {
    return (
      <Screen scroll>
        <SkeletonListe lignes={3} />
      </Screen>
    );
  }
  return <Formulaire id={id} initiales={initiales} />;
}

function Formulaire({ id, initiales }: { id?: string; initiales: Criteres }) {
  const router = useRouter();
  const creer = useCreerAlerte();
  const modifier = useModifierAlerte(id ?? "");
  const mutation = id ? modifier : creer;
  const [criteres, setCriteres] = useState<Criteres>(initiales);

  return (
    <Screen
      scroll
      footer={
        <Button
          titre={id ? t.commun.enregistrer : "Créer l’alerte"}
          chargement={mutation.isPending}
          onPress={() =>
            mutation.mutate(versCorps(criteres), {
              onSuccess: () => {
                router.back();
                if (!id) void proposerNotifications("alerte");
              },
            })
          }
        />
      }
    >
      <Text variante="titre">{id ? "Modifier l’alerte" : "Nouvelle alerte"}</Text>
      <Text muted>Choisis tes critères : tu reçois une notification dès qu’une chambre correspond. Sans critère, tu es prévenu de toutes les nouvelles chambres.</Text>
      <EditeurCriteres valeur={criteres} onChange={setCriteres} />
      {mutation.error ? (
        <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
          {isApiError(mutation.error) ? messageErreur(mutation.error.code, mutation.error.message) : t.erreurs.network}
        </Text>
      ) : null}
    </Screen>
  );
}
