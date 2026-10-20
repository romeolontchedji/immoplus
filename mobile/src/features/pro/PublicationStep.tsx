import { Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { Image } from "expo-image";
import { isApiError } from "@/api/errors";
import { francs } from "@/lib/format";
import { urlMedia } from "@/lib/media";
import { messageErreur, t } from "@/i18n/fr";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { PHOTOS_MIN, useBrouillon } from "./brouillon";
import { useActionAnnonce, useAnnoncePro, useMediasPro } from "./queries";
import { EntetePublication } from "./EntetePublication";

type LigneApercuProps = { label: string; valeur: string; onModifier: () => void };

/** Ligne du tableau d'aperçu "Infos / Vidéo + photos / Description" avec lien "Modifier" */
function LigneApercu({ label, valeur, onModifier }: LigneApercuProps) {
  const { c } = useTheme();
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        paddingVertical: sp[3],
        borderBottomWidth: 1,
        borderBottomColor: c.divider,
      }}
    >
      <Text muted>{label}</Text>
      <Pressable accessibilityRole="button" onPress={onModifier} style={{ paddingLeft: sp[3] }}>
        <Text variante="lien">Modifier</Text>
      </Pressable>
    </View>
  );
}

/**
 * Étape de publication — aperçu final (EF-ANN-06, EF-ANN-11).
 * Conforme à la maquette « Mobile · Publier 4 4@1x.png » :
 * - Titre "Tout est bon ?" · sous-titre "Vérifie l'aperçu avant de publier"
 * - Vignette vidéo/photo avec bouton play (dégradé bleu nuit)
 * - Titre + loyer + détails de l'annonce
 * - Tableau : Infos / Vidéo + N photos / Description + lien "Modifier" à droite
 * - Badge "✓ Prête à publier" en vert
 * - Bouton "Publier la chambre" jaune solaire (#FDB836) en pied de page
 */
export function PublicationStep() {
  const { c } = useTheme();
  const router = useRouter();
  const { brouillon, effacer } = useBrouillon();
  const id = brouillon.serveurId;
  const annonce = useAnnoncePro(id);
  const medias = useMediasPro(id);
  const publier = useActionAnnonce(id ?? "");

  const nbPhotos = (medias.data ?? []).filter((m) => m.kind === "photo").length;
  const hasVideo = (medias.data ?? []).some((m) => m.kind === "video");
  const cover = (medias.data ?? []).find((m) => m.is_cover);

  const lancer = () => {
    publier.mutate("publish", {
      onSuccess: () => {
        effacer();
        router.replace("/pro/annonces" as never);
      },
    });
  };

  const prete = !!(id && hasVideo && nbPhotos >= PHOTOS_MIN);

  return (
    <Screen
      scroll
      footer={
        <Button
          titre="Publier la chambre"
          chargement={publier.isPending}
          variante="accent" // jaune solaire (maquette Publier 4/4)
          onPress={lancer}
        />
      }
    >
      <EntetePublication etape={6} total={6} />

      <Text variante="titre" style={{ marginTop: sp[2] }}>Tout est bon ?</Text>
      <Text muted>Vérifie l’aperçu avant de publier.</Text>

      {/* Vignette vidéo/photo avec bouton play */}
      <View
        style={{
          height: 180,
          borderRadius: rayon.card,
          backgroundColor: colors.night,
          overflow: "hidden",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {urlMedia(cover?.poster_url) ? (
          <Image source={{ uri: urlMedia(cover?.poster_url) }} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }} contentFit="cover" accessibilityIgnoresInvertColors />
        ) : null}
        <View style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(15,27,61,0.35)" }} />
        <View style={{ width: 56, height: 56, borderRadius: 28, backgroundColor: "rgba(255,255,255,0.92)", alignItems: "center", justifyContent: "center" }}>
          <View style={{ width: 0, height: 0, borderTopWidth: 10, borderBottomWidth: 10, borderLeftWidth: 18, borderTopColor: "transparent", borderBottomColor: "transparent", borderLeftColor: colors.blue, marginLeft: 4 }} />
        </View>
      </View>

      {/* Infos résumées */}
      {annonce.data ? (
        <View
          style={{
            backgroundColor: c.surface,
            borderRadius: rayon.card,
            padding: sp[4],
            gap: 2,
          }}
        >
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}>
            <Text variante="corpsGras" numberOfLines={1} style={{ flex: 1 }}>{annonce.data.title}</Text>
            <Text variante="corpsGras" couleur={c.primary}>{francs(annonce.data.rent_amount)}</Text>
          </View>
          <Text variante="legende" muted>
            {annonce.data.district_name}{annonce.data.deposit_months ? ` · Caution ${annonce.data.deposit_months} mois` : ""}
          </Text>
        </View>
      ) : null}

      {/* Tableau d'aperçu avec liens Modifier */}
      <View style={{ backgroundColor: c.surface, borderRadius: rayon.card, padding: sp[4] }}>
        <LigneApercu label="Infos" valeur="" onModifier={() => router.push("/pro/nouvelle-annonce/infos" as never)} />
        <LigneApercu
          label={`Vidéo${nbPhotos > 0 ? ` + ${nbPhotos} photo${nbPhotos > 1 ? "s" : ""}` : ""}`}
          valeur=""
          onModifier={() => router.push("/pro/nouvelle-annonce/medias" as never)}
        />
        <LigneApercu label="Description" valeur="" onModifier={() => router.push("/pro/nouvelle-annonce/description" as never)} />
      </View>

      {/* Badge de statut de publication */}
      {prete ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: c.succes }} />
          <Text variante="legende" couleur={c.succesText} style={{ fontWeight: "700" }}>
            Prête à publier · visible tout de suite par les étudiants
          </Text>
        </View>
      ) : (
        <Text variante="legende" couleur={c.danger}>
          {!hasVideo ? "Ajoute une vidéo. " : ""}
          {nbPhotos < PHOTOS_MIN ? `Ajoute au moins ${PHOTOS_MIN - nbPhotos} photo${PHOTOS_MIN - nbPhotos > 1 ? "s" : ""} de plus.` : ""}
        </Text>
      )}

      {publier.error ? (
        <Text variante="legende" couleur={c.danger} accessibilityLiveRegion="polite">
          {isApiError(publier.error) ? messageErreur(publier.error.code, publier.error.message) : "Une erreur est survenue."}
        </Text>
      ) : null}
    </Screen>
  );
}
