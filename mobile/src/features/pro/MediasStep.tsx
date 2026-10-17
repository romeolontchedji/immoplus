import { useState } from "react";
import { Pressable, View } from "react-native";
import { useRouter } from "expo-router";
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
import { useMediasPro } from "./queries";
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
  const id = brouillon.serveurId;
  const medias = useMediasPro(id);
  const [envoi, setEnvoi] = useState<{ libelle: string; ratio: number } | null>(null);
  const [erreurEnvoi, setErreurEnvoi] = useState<unknown>(null);

  /** Envoie les fichiers un par un en affichant la progression ; une erreur s'affiche sous la zone vidéo. */
  const envoyer = async (fichiers: { uri: string; kind: "video" | "photo" }[]) => {
    if (!id) { router.push("/pro/nouvelle-annonce/infos" as never); return; }
    setErreurEnvoi(null);
    try {
      for (const [i, f] of fichiers.entries()) {
        const libelle = f.kind === "video" ? "Envoi de la vidéo" : `Envoi de la photo ${i + 1}/${fichiers.length}`;
        setEnvoi({ libelle, ratio: 0 });
        await ajouterMedia({ annonceId: id, uri: f.uri, kind: f.kind, surProgression: (ratio) => setEnvoi({ libelle, ratio }) });
      }
    } catch (e) {
      setErreurEnvoi(e);
    } finally {
      setEnvoi(null);
      void medias.refetch();
    }
  };

  const choisirVideo = async () => {
    const r = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["videos"],
      quality: 1,
      videoMaxDuration: 60,
    });
    if (r.canceled || !r.assets[0]) return;
    await envoyer([{ uri: r.assets[0].uri, kind: "video" }]);
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

  const videos = medias.data?.filter((m) => m.kind === "video") ?? [];
  const photos = medias.data?.filter((m) => m.kind === "photo") ?? [];
  const hasVideo = videos.length > 0;

  return (
    <Screen scroll footer={
      <Button
        titre="Continuer"
        onPress={() => router.push("/pro/nouvelle-annonce/description" as never)}
      />
    }>
      <EntetePublication etape={5} total={6} />

      <Text variante="titre" style={{ marginTop: sp[2] }}>Montre-la en vidéo</Text>
      <Text muted>Une vidéo rassure et fait gagner du temps à tout le monde.</Text>

      {/* Zone vidéo pointillée (conforme maquette Publier 2/4) */}
      <Pressable
        accessibilityRole="button"
        onPress={choisirVideo}
        disabled={!!envoi}
        style={({ pressed }) => ({
          borderWidth: 2,
          borderStyle: "dashed",
          borderColor: hasVideo ? c.succes : c.primary,
          borderRadius: rayon.card,
          backgroundColor: hasVideo ? c.succesBg : c.primarySoft,
          padding: sp[6],
          alignItems: "center",
          justifyContent: "center",
          gap: sp[2],
          opacity: pressed ? 0.8 : 1,
          minHeight: 140,
        })}
      >
        {hasVideo ? (
          <>
            <View style={{ width: 0, height: 0, borderTopWidth: 10, borderBottomWidth: 10, borderLeftWidth: 18, borderTopColor: "transparent", borderBottomColor: "transparent", borderLeftColor: c.succes }} />
            <Text variante="corpsGras" couleur={c.succes}>Vidéo ajoutée</Text>
            <Text variante="legende" muted>Appuie pour remplacer</Text>
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

      {envoi ? (
        <View style={{ gap: sp[2] }}>
          <Text variante="legende" couleur={c.primary} style={{ fontWeight: "700" }}>{envoi.libelle} · {Math.round(envoi.ratio * 100)} %</Text>
          <View style={{ height: 6, borderRadius: 3, backgroundColor: c.primarySoft, overflow: "hidden" }}>
            <View style={{ height: 6, width: `${Math.round(envoi.ratio * 100)}%`, backgroundColor: c.primary }} />
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
              {urlMedia(photo.poster_url ?? photo.playback_url) ? (
                <Image source={{ uri: urlMedia(photo.poster_url ?? photo.playback_url) }} style={{ width: "100%", height: "100%" }} contentFit="cover" accessibilityIgnoresInvertColors />
              ) : (
                <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
                  <View style={{ width: 20, height: 20, borderRadius: 4, backgroundColor: c.primary, opacity: 0.6 }} />
                </View>
              )}
            </View>
          ))}
        </View>
        <Text variante="legende" muted>La première photo sera la couverture de l’annonce.</Text>
      </View>
    </Screen>
  );
}
