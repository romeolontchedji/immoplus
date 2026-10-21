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
import { aUnCritere, criteresDe, criteresDepuisFiltres, EditeurCriteres, versCorps, type Criteres } from "./EditeurCriteres";
import { useAlertes, useCreerAlerte, useModifierAlerte } from "./queries";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { useSession } from "@/state/session";

/**
 * Création et modification d'une alerte (EF-ALR-01). /nouvelle-alerte part de la recherche en cours ;
 * /modifier-alerte/[id] préremplit l'alerte puis envoie un PATCH.
 */
export function AlerteFormScreen() {
  const { etat } = useSession();
  // Créer une alerte exige un compte (plan v3, H3) : on le demande avant le formulaire, pas après.
  if (etat.statut !== "connecte") {
    return (
      <Screen scroll>
        <AuthRequired />
      </Screen>
    );
  }
  return <AlerteFormConnecte />;
}

function AlerteFormConnecte() {
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
  const [vide, setVide] = useState(false);
  const changer = (c: Criteres) => {
    setCriteres(c);
    setVide(false);
  };

  return (
    <Screen
      scroll
      footer={
        <Button
          titre={id ? t.commun.enregistrer : "Créer l’alerte"}
          chargement={mutation.isPending}
          onPress={() => {
            // Aucune option choisie : pas d'alerte (demande du 2026-10-20).
            if (!aUnCritere(criteres)) return setVide(true);
            mutation.mutate(versCorps(criteres), {
              onSuccess: () => {
                router.back();
                if (!id) void proposerNotifications("alerte");
              },
            });
          }}
        />
      }
    >
      <Text variante="titre">{id ? "Modifier l’alerte" : "Nouvelle alerte"}</Text>
      <Text muted>Choisis au moins une option : tu reçois une notification dès qu’une chambre correspond.</Text>
      <EditeurCriteres valeur={criteres} onChange={changer} />
      {vide ? (
        <Text variante="corpsGras" couleur={colors.danger} accessibilityLiveRegion="polite">
          {t.erreurs.alert_empty}
        </Text>
      ) : null}
      {mutation.error ? (
        <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
          {isApiError(mutation.error) ? messageErreur(mutation.error.code, mutation.error.message) : t.erreurs.network}
        </Text>
      ) : null}
    </Screen>
  );
}
