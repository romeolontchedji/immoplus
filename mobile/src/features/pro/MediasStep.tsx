import { useState } from "react";
import { ActivityIndicator, Alert, Pressable, View } from "react-native";
import { CircleAlert, X } from "lucide-react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { QueryState } from "@/ui/components/States";
import { Text } from "@/ui/components/Text";
import { useBrouillon } from "./brouillon";
import { useMediasPro, useSupprimerMedia } from "./queries";
import { ajouterMedia } from "./envoi";
import { urlMedia } from "@/lib/media";
import { EntetePublication } from "./EntetePublication";

/**
 * Étape 3/4 — Médias : vidéo + photos (EF-MED-01 à EF-MED-08).
 * Conforme à la maquette « Mobile · Publier 2 4@1x.png » :
 * - Zone vidéo pointillée bleue avec texte "▶ Ajouter la visite vidéo"
 * - Astuce : bandeau jaune "les chambres avec vidéo reçoivent plus de contacts"
 * - Grille de photos : bouton "+ Ajouter" + vignettes téléversées
 */
export function MediasStep() {
  const { c } = useTheme();
  const router = useRouter();
  const { brouillon, maj } = useBrouillon();
  // `?annonce=` : médias d'une annonce existante, depuis sa fiche gérant (hors assistant de création).
  const { annonce } = useLocalSearchParams<{ annonce?: string }>();
  const id = annonce ?? brouillon.serveurId;
  const medias = useMediasPro(id);
  const supprimer = useSupprimerMedia(id);
  const [envoi, setEnvoi] = useState<{ libelle: string; ratio: number } | null>(null);
  const [erreurEnvoi, setErreurEnvoi] = useState<unknown>(null);

  /** Envoie les fichiers un par un en affichant la progression ; une erreur s'affiche sous la zone vidéo. */
  const envoyer = async (fichiers: { uri: string; kind: "video" | "photo" }[], avant?: () => Promise<unknown>) => {
    if (!id) { router.push("/pro/nouvelle-annonce/infos" as never); return; }
    setErreurEnvoi(null);
    try {
      if (avant) {
        setEnvoi({ libelle: "Retrait de l'ancienne vidéo", ratio: 0 });
        await avant();
      }
      for (const [i, f] of fichiers.entries()) {
        const nom = f.kind === "video" ? "la vidéo" : `la photo ${i + 1}/${fichiers.length}`;
        await ajouterMedia({
          annonceId: id, uri: f.uri, kind: f.kind,
          surProgression: (ratio, etape) => setEnvoi({ libelle: etape === "preparation" ? `Préparation de ${nom}` : `Envoi de ${nom}`, ratio }),
        });
      }
    } catch (e) {
      setErreurEnvoi(e);
    } finally {
      setEnvoi(null);
      void medias.refetch();
    }
  };

  const videos = medias.data?.filter((m) => m.kind === "video") ?? [];
  const photos = medias.data?.filter((m) => m.kind === "photo") ?? [];
  // Vidéo qui compte : la plus récente qui n'a pas échoué, sinon la dernière en échec (pour l'expliquer).
  const video = videos.filter((v) => v.status !== "failed").at(-1) ?? videos.at(-1);
  const etatVideo = envoi ? "envoi" : video?.status === "uploaded" || video?.status === "processing" ? "traitement" : video?.status;
  const hasVideo = etatVideo === "ready";

  const lancerChoixVideo = async () => {
    const r = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["videos"],
      quality: 1,
      videoMaxDuration: 60,
    });
    if (r.canceled || !r.assets[0]) return;
    // Une seule vidéo par annonce : l'ancienne (prête ou envoi interrompu) est retirée juste avant l'envoi.
    const ancienne = video && (video.status === "ready" || video.status === "uploading") ? video.id : null;
    await envoyer([{ uri: r.assets[0].uri, kind: "video" }], ancienne ? () => supprimer.mutateAsync(ancienne) : undefined);
  };

  const choisirVideo = () => {
    if (etatVideo === "traitement") return;
    if (!hasVideo) { void lancerChoixVideo(); return; }
    Alert.alert("Remplacer la vidéo ?", "L'ancienne vidéo sera supprimée et remplacée par la nouvelle.", [
      { text: "Annuler", style: "cancel" },
      { text: "Choisir une vidéo", onPress: () => void lancerChoixVideo() },
    ]);
  };

  const retirerPhoto = (mediaId: string) => {
    Alert.alert("Retirer cette photo ?", "Elle disparaîtra de l'annonce.", [
      { text: "Annuler", style: "cancel" },
      { text: "Retirer", style: "destructive", onPress: () => supprimer.mutate(mediaId, { onError: setErreurEnvoi }) },
    ]);
  };

  const choisirPhoto = async () => {
    const r = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.85,
      allowsMultipleSelection: true,
      selectionLimit: 10,
    });
    if (r.canceled) return;
    await envoyer(r.assets.map((a) => ({ uri: a.uri, kind: "photo" as const })));
  };

  const pourcent = envoi ? Math.round(envoi.ratio * 100) : 0;

  return (
    <Screen scroll footer={
      <Button
        titre={annonce ? "Terminer" : "Continuer"}
        onPress={() => (annonce ? router.back() : router.push("/pro/nouvelle-annonce/description" as never))}
      />
    }>
      {annonce ? null : <EntetePublication etape={5} total={6} />}

      <Text variante="titre" style={{ marginTop: sp[2] }}>Montre-la en vidéo</Text>
      <Text muted>Une vidéo rassure et fait gagner du temps à tout le monde.</Text>

      {/* Zone vidéo pointillée (conforme maquette Publier 2/4) */}
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ busy: etatVideo === "envoi" || etatVideo === "traitement" }}
        onPress={choisirVideo}
        disabled={!!envoi || etatVideo === "traitement"}
        style={({ pressed }) => ({
          borderWidth: 2,
          borderStyle: "dashed",
          borderColor: hasVideo ? c.succes : etatVideo === "failed" ? c.danger : c.primary,
          borderRadius: rayon.card,
          backgroundColor: hasVideo ? c.succesBg : etatVideo === "failed" ? c.dangerBg : c.primarySoft,
          padding: sp[6],
          alignItems: "center",
          justifyContent: "center",
          gap: sp[2],
          opacity: pressed ? 0.8 : 1,
          minHeight: 140,
        })}
      >
        {etatVideo === "envoi" && envoi ? (
          <View style={{ alignSelf: "stretch", alignItems: "center", gap: sp[2] }} accessibilityLiveRegion="polite">
            <ActivityIndicator color={c.primary} />
            <Text variante="corpsGras" couleur={c.primary}>{envoi.libelle} · {pourcent} %</Text>
            <View style={{ alignSelf: "stretch", height: 8, borderRadius: 4, backgroundColor: c.surface, overflow: "hidden" }}>
              <View style={{ height: 8, width: `${pourcent}%`, backgroundColor: c.primary }} />
            </View>
            <Text variante="legende" muted style={{ textAlign: "center" }}>Garde l’application ouverte jusqu’à la fin de l’envoi.</Text>
          </View>
        ) : etatVideo === "traitement" ? (
          <>
            <ActivityIndicator color={c.primary} />
            <Text variante="corpsGras" couleur={c.primary}>Vidéo reçue, préparation en cours…</Text>
            <Text variante="legende" muted style={{ textAlign: "center" }}>Le serveur la convertit pour qu’elle se lise partout. Cela prend environ une minute.</Text>
          </>
        ) : etatVideo === "failed" ? (
          <>
            <CircleAlert size={24} color={c.danger} />
            <Text variante="corpsGras" couleur={c.danger}>La vidéo n’a pas pu être préparée</Text>
            <Text variante="legende" muted style={{ textAlign: "center" }}>{video?.error_detail ?? "Réessaie avec une autre vidéo."} Appuie pour en choisir une autre.</Text>
          </>
        ) : etatVideo === "uploading" ? (
          <>
            <CircleAlert size={24} color={c.primary} />
            <Text variante="corpsGras" couleur={c.primary}>Envoi interrompu</Text>
            <Text variante="legende" muted>Appuie pour choisir la vidéo à nouveau</Text>
          </>
        ) : hasVideo ? (
          <>
            <View style={{ width: 0, height: 0, borderTopWidth: 10, borderBottomWidth: 10, borderLeftWidth: 18, borderTopColor: "transparent", borderBottomColor: "transparent", borderLeftColor: c.succes }} />
            <Text variante="corpsGras" couleur={c.succes}>Vidéo en ligne</Text>
            <Text variante="legende" muted>Appuie pour la remplacer</Text>
          </>
        ) : (
          <>
            <View style={{ width: 0, height: 0, borderTopWidth: 10, borderBottomWidth: 10, borderLeftWidth: 18, borderTopColor: "transparent", borderBottomColor: "transparent", borderLeftColor: c.primary }} />
            <Text variante="corpsGras" couleur={c.primary}>Ajouter la visite vidéo</Text>
            <Text variante="legende" muted style={{ textAlign: "center" }}>
              20 à 30 secondes · filme l’entrée, la chambre, la douche
            </Text>
          </>
        )}
      </Pressable>

      {/* Envoi de photos : la progression s'affiche sous la zone vidéo. */}
      {envoi && !envoi.libelle.includes("vidéo") ? (
        <View style={{ gap: sp[2] }} accessibilityLiveRegion="polite">
          <Text variante="legende" couleur={c.primary} style={{ fontWeight: "700" }}>{envoi.libelle} · {pourcent} %</Text>
          <View style={{ height: 6, borderRadius: 3, backgroundColor: c.primarySoft, overflow: "hidden" }}>
            <View style={{ height: 6, width: `${pourcent}%`, backgroundColor: c.primary }} />
          </View>
        </View>
      ) : null}
      {erreurEnvoi ? (
        <Text variante="legende" couleur={c.danger} accessibilityLiveRegion="polite">
          {isApiError(erreurEnvoi) ? messageErreur(erreurEnvoi.code, erreurEnvoi.message) : "L'envoi a échoué. Vérifie ta connexion et réessaie."}
        </Text>
      ) : null}

      {/* Astuce jaune (conforme maquette) */}
      {!hasVideo ? (
        <View
          style={{
            backgroundColor: c.avertissementBg,
            borderRadius: rayon.card,
            padding: sp[3],
          }}
        >
          <Text variante="legende" couleur={c.avertissementText}>
            <Text variante="legende" couleur={c.avertissementText} style={{ fontWeight: "700" }}>Astuce : </Text>
            les chambres avec vidéo reçoivent plus de contacts.
          </Text>
        </View>
      ) : null}

      {/* Photos */}
      <View style={{ gap: sp[3] }}>
        <Text variante="sousTitre">Photos (3 minimum)</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          {/* Bouton + Ajouter */}
          <Pressable
            accessibilityRole="button"
            onPress={choisirPhoto}
            disabled={!!envoi}
            style={({ pressed }) => ({
              width: 72,
              height: 72,
              borderRadius: 12,
              borderWidth: 1.5,
              borderStyle: "dashed",
              borderColor: c.border,
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: pressed ? c.divider : c.surface,
            })}
          >
            <Text muted style={{ fontSize: 18 }}>+</Text>
            <Text variante="legende" muted style={{ fontSize: 11 }}>Ajouter</Text>
          </Pressable>

          {/* Vignettes */}
          {photos.map((photo, i) => (
            <View
              key={photo.id}
              style={{
                width: 72,
                height: 72,
                borderRadius: 12,
                overflow: "hidden",
                backgroundColor: colors.night,
                borderWidth: i === 0 ? 2 : 0,
                borderColor: i === 0 ? c.primary : undefined,
              }}
            >
              {photo.status === "ready" && urlMedia(photo.poster_url ?? photo.playback_url) ? (
                <Image source={{ uri: urlMedia(photo.poster_url ?? photo.playback_url) }} style={{ width: "100%", height: "100%" }} contentFit="cover" accessibilityIgnoresInvertColors />
              ) : (
                <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: photo.status === "failed" ? c.dangerBg : c.primarySoft }}>
                  {photo.status === "failed" ? <CircleAlert size={20} color={c.danger} /> : <ActivityIndicator color={c.primary} />}
                </View>
              )}
              {photo.status === "processing" || photo.status === "uploaded" ? null : (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Retirer la photo ${i + 1}`}
                  onPress={() => retirerPhoto(photo.id)}
                  disabled={!!envoi || supprimer.isPending}
                  hitSlop={8}
                  style={{ position: "absolute", top: 4, right: 4, width: 22, height: 22, borderRadius: 11, backgroundColor: colors.night, opacity: 0.85, alignItems: "center", justifyContent: "center" }}
                >
                  <X size={14} color={colors.white} />
                </Pressable>
              )}
            </View>
          ))}
        </View>
        <Text variante="legende" muted>La première photo sera la couverture de l’annonce.</Text>
      </View>
    </Screen>
  );
}
