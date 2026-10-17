import { useEffect, useState } from "react";
import { Pressable, ScrollView, Share, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Image } from "expo-image";
import { useVideoPlayer, VideoView } from "expo-video";
import { ArrowLeft, BadgeCheck, Bell, Flag, Heart, MapPin, Play, Share2 } from "lucide-react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { WEB_HOST } from "@/config/env";
import { dateCourte, distance, francs } from "@/lib/format";
import { urlMedia } from "@/lib/media";
import { t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { ErrorState, OfflineBanner } from "@/ui/components/States";
import { Skeleton } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { LIBELLES_EAU } from "./filtres";
import { useBasculerFavori, useCompterVue, useFiche, type Fiche } from "./queries";

type Media = Fiche["media"][number];

const COMPTEUR: Record<string, string> = { individual: "Compteur individuel", shared: "Compteur partagé" };

/** Délai de réponse médian du gérant, en clair. */
function delaiReponse(min: number | null | undefined): string | null {
  if (min == null) return null;
  if (min < 60) return `Répond en ${Math.max(1, Math.round(min))} min environ`;
  const h = Math.round(min / 60);
  return h < 24 ? `Répond en ${h} h environ` : `Répond en ${Math.round(h / 24)} j environ`;
}

function initiales(nom: string | null | undefined): string {
  return (nom ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((m) => m[0]?.toUpperCase() ?? "")
    .join("") || "G";
}

/** Image d'un média : vignette de la vidéo, sinon la photo. */
const imageDe = (m: Media | undefined) => urlMedia(m ? (m.kind === "video" ? m.poster_url : (m.url ?? m.thumb_url)) : null);

function LecteurVideo({ uri }: { uri: string }) {
  const lecteur = useVideoPlayer(uri, (p) => p.play());
  return <VideoView player={lecteur} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }} nativeControls contentFit="contain" />;
}

function Ligne({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: sp[3], borderBottomWidth: 1, borderBottomColor: colors.divider, gap: sp[3] }}>
      <Text muted>{libelle}</Text>
      <Text variante="corpsGras" style={{ flexShrink: 1, textAlign: "right" }}>{valeur}</Text>
    </View>
  );
}

function BoutonRond({ libelle, onPress, children }: { libelle: string; onPress: () => void; children: React.ReactNode }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={libelle}
      onPress={onPress}
      hitSlop={6}
      style={({ pressed }) => ({ width: 42, height: 42, borderRadius: 21, backgroundColor: pressed ? colors.divider : colors.white, alignItems: "center", justifyContent: "center", ...ombre.card })}
    >
      {children}
    </Pressable>
  );
}

/**
 * Fiche d'annonce (EF-REC-06 à EF-REC-10, maquette Mobile · Détail chambre). Ne lit que les champs de `FicheOut` :
 * médias (vidéo lisible, photos), loyer et conditions, équipements, gérant (nom, vérifié, délai médian), description.
 */
export function FicheScreen() {
  const router = useRouter();
  const haut = useSafeAreaInsets().top;
  const { ident } = useLocalSearchParams<{ ident: string }>();
  const { etat } = useSession();
  const requete = useFiche(ident);
  const compterVue = useCompterVue();
  const basculerFavori = useBasculerFavori();
  const [mediaActif, setMediaActif] = useState<string | null>(null);
  const [lecture, setLecture] = useState(false);
  const [descriptionOuverte, setDescriptionOuverte] = useState(false);

  useEffect(() => {
    if (ident) compterVue.mutate(ident);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ident]);

  const retour = () => (router.canGoBack() ? router.back() : router.replace("/"));

  if (requete.isError) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
        <View style={{ padding: sp[4] }}>
          <BoutonRond libelle={t.commun.retour} onPress={retour}><ArrowLeft size={20} color={colors.night} /></BoutonRond>
        </View>
        <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} />
      </SafeAreaView>
    );
  }

  if (!requete.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["bottom"]}>
        <View style={{ height: 300, backgroundColor: colors.night }} />
        <View style={{ padding: sp[4], gap: sp[3] }}>
          <Skeleton hauteur={28} />
          <Skeleton hauteur={18} largeur="60%" />
          <Skeleton hauteur={90} />
        </View>
      </SafeAreaView>
    );
  }

  const fiche = requete.data;
  const medias = fiche.media ?? [];
  const video = medias.find((m) => m.kind === "video");
  const couverture = medias.find((m) => m.id === mediaActif) ?? medias.find((m) => m.is_cover) ?? medias[0];
  const image = imageDe(couverture);
  const lien = `https://${WEB_HOST}/annonces/${fiche.slug}`;

  const equipements = [
    fiche.has_private_bathroom ? "Douche interne" : null,
    fiche.is_fenced ? "Cour clôturée" : null,
    LIBELLES_EAU[fiche.water_source] ?? null,
    COMPTEUR[fiche.electricity_meter] ?? null,
  ].filter((x): x is string => !!x);

  const basculer = () => {
    if (etat.statut !== "connecte") return router.push("/connexion");
    basculerFavori.mutate({ id: fiche.id, ident: fiche.slug, actif: !fiche.is_favorite });
  };
  const contacter = () => {
    if (etat.statut !== "connecte") return router.push("/connexion");
    router.push(`/conversation/nouvelle?listing=${fiche.id}` as never);
  };

  const delai = delaiReponse(fiche.gerant?.median_response_min);
  const description = fiche.description_md?.trim();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["bottom"]}>
      <OfflineBanner />
      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ flexGrow: 1 }} bounces={false}>
        {/* Média principal */}
        <View style={{ height: 300 + haut, backgroundColor: colors.night, justifyContent: "center", alignItems: "center" }}>
          {lecture && video ? (
            <LecteurVideo uri={urlMedia(video.playback_url) ?? ""} />
          ) : (
            <>
              <Image
                source={image ? { uri: image } : require("../../../assets/illustration-chambres.svg")}
                style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
                contentFit="cover"
                transition={150}
                accessibilityIgnoresInvertColors
              />
              <View style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(15,27,61,0.20)" }} />
              {video ? (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Lire la vidéo de la chambre"
                  onPress={() => setLecture(true)}
                  style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: colors.white, alignItems: "center", justifyContent: "center", ...ombre.pop }}
                >
                  <Play size={26} color={colors.primary} fill={colors.primary} style={{ marginLeft: 4 }} />
                </Pressable>
              ) : null}
              {video?.duration_s ? (
                <View style={{ position: "absolute", bottom: sp[8], right: sp[4], backgroundColor: "rgba(0,0,0,0.55)", borderRadius: 8, paddingHorizontal: sp[2], paddingVertical: 3 }}>
                  <Text style={{ color: colors.white, fontSize: 12, fontWeight: "700" }}>
                    {`${Math.floor(video.duration_s / 60)}:${String(Math.round(video.duration_s % 60)).padStart(2, "0")}`}
                  </Text>
                </View>
              ) : null}
            </>
          )}
        </View>

        {/* Boutons superposés */}
        <View style={{ position: "absolute", top: haut + sp[2], left: 0, right: 0, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: sp[4] }}>
          <BoutonRond libelle={t.commun.retour} onPress={retour}><ArrowLeft size={20} color={colors.night} /></BoutonRond>
          <View style={{ flexDirection: "row", gap: sp[2] }}>
            <BoutonRond libelle="Partager" onPress={() => void Share.share({ message: `${fiche.title} · ${francs(fiche.rent_amount)}/mois sur Logeo\n${lien}` })}>
              <Share2 size={18} color={colors.night} />
            </BoutonRond>
            <BoutonRond libelle={fiche.is_favorite ? "Retirer des favoris" : "Ajouter aux favoris"} onPress={basculer}>
              <Heart size={19} color={fiche.is_favorite ? colors.danger : colors.night} fill={fiche.is_favorite ? colors.danger : "transparent"} />
            </BoutonRond>
          </View>
        </View>

        {/* Feuille blanche */}
        <View style={{ backgroundColor: colors.bg, borderTopLeftRadius: rayon.sheet, borderTopRightRadius: rayon.sheet, marginTop: -28, padding: sp[4], paddingTop: sp[5], gap: sp[5], flex: 1 }}>
          {medias.length > 1 ? (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: sp[2] }}>
              {medias.map((m) => {
                const vignette = urlMedia(m.thumb_url ?? m.poster_url ?? m.url);
                const actif = m.id === couverture?.id;
                return (
                  <Pressable
                    key={m.id}
                    accessibilityRole="button"
                    accessibilityLabel={m.kind === "video" ? "Vidéo" : "Photo"}
                    onPress={() => {
                      setLecture(false);
                      setMediaActif(m.id);
                    }}
                    style={{ width: 72, height: 56, borderRadius: 12, overflow: "hidden", borderWidth: 2, borderColor: actif ? colors.primary : "transparent", backgroundColor: colors.night, alignItems: "center", justifyContent: "center" }}
                  >
                    {vignette ? <Image source={{ uri: vignette }} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }} contentFit="cover" /> : null}
                    {m.kind === "video" ? <Play size={16} color={colors.white} fill={colors.white} /> : null}
                  </Pressable>
                );
              })}
            </ScrollView>
          ) : null}

          <View style={{ gap: sp[2] }}>
            <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: sp[3] }}>
              <View style={{ flex: 1, gap: 4 }}>
                <Text variante="label" couleur={colors.primary}>{t.typeChambre[fiche.room_type] ?? fiche.room_type}</Text>
                <Text variante="titreSection">{fiche.title}</Text>
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={{ fontSize: 22, fontWeight: "800", color: colors.primary }}>{francs(fiche.rent_amount)}</Text>
                <Text variante="legende" muted>par mois</Text>
              </View>
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              <MapPin size={15} color={colors.textMuted} />
              <Text variante="legende" muted style={{ flex: 1 }}>
                {[fiche.district?.name, fiche.landmark_text, fiche.distance_m != null ? `${distance(fiche.distance_m)} de l'UP` : null].filter(Boolean).join(" · ")}
              </Text>
            </View>
            {fiche.status !== "published" ? (
              <Text variante="corpsGras" couleur={colors.warning}>{t.statutAnnonce[fiche.status] ?? fiche.status}</Text>
            ) : fiche.last_confirmed_at ? (
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: colors.success }} />
                <Text variante="legende" couleur={colors.successText} style={{ fontWeight: "700" }}>
                  Disponibilité confirmée le {dateCourte(fiche.last_confirmed_at)}
                </Text>
              </View>
            ) : null}
          </View>

          {equipements.length ? (
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
              {equipements.map((eq) => (
                <View key={eq} style={{ paddingHorizontal: sp[3], paddingVertical: sp[2], borderRadius: rayon.pilule, borderWidth: 1.5, borderColor: colors.border, backgroundColor: colors.surface }}>
                  <Text style={{ fontSize: 13, fontWeight: "700", color: colors.night }}>{eq}</Text>
                </View>
              ))}
            </View>
          ) : null}

          {/* Gérant */}
          <View style={{ flexDirection: "row", alignItems: "center", gap: sp[3], padding: sp[4], backgroundColor: colors.surface, borderRadius: rayon.card, borderWidth: 1, borderColor: colors.border }}>
            <View style={{ width: 46, height: 46, borderRadius: 23, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center" }}>
              <Text style={{ fontWeight: "800", color: colors.primary }}>{initiales(fiche.gerant?.name)}</Text>
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2], flexWrap: "wrap" }}>
                <Text variante="corpsGras">{fiche.gerant?.name ?? "Gérant"}</Text>
                {fiche.gerant?.verified ? (
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: colors.successBg, borderRadius: rayon.pilule, paddingHorizontal: sp[2], paddingVertical: 2 }}>
                    <BadgeCheck size={13} color={colors.successText} />
                    <Text style={{ fontSize: 12, fontWeight: "700", color: colors.successText }}>Vérifié</Text>
                  </View>
                ) : null}
              </View>
              <Text variante="legende" muted>{delai ?? "Gérant de la chambre"}</Text>
            </View>
          </View>

          {/* Conditions */}
          <View>
            <Text variante="label" muted style={{ marginBottom: sp[1] }}>Conditions</Text>
            <Ligne libelle="Loyer" valeur={`${francs(fiche.rent_amount)} / mois`} />
            {fiche.deposit_months ? <Ligne libelle="Caution" valeur={`${fiche.deposit_months} mois`} /> : null}
            {fiche.advance_months ? <Ligne libelle="Avance" valeur={`${fiche.advance_months} mois`} /> : null}
            <Ligne libelle="Frais d'agence" valeur={fiche.agent_fee_amount ? francs(fiche.agent_fee_amount) : "Aucun"} />
            {fiche.available_from ? <Ligne libelle="Disponible dès le" valeur={dateCourte(fiche.available_from)} /> : null}
          </View>

          {description ? (
            <View style={{ gap: sp[2] }}>
              <Text variante="label" muted>Description</Text>
              <Text style={{ fontSize: 15, lineHeight: 23, color: colors.night }} numberOfLines={descriptionOuverte ? undefined : 6}>{description}</Text>
              {description.length > 240 ? (
                <Pressable accessibilityRole="button" onPress={() => setDescriptionOuverte((v) => !v)} hitSlop={8}>
                  <Text variante="lien" style={{ fontWeight: "700" }}>{descriptionOuverte ? "Réduire" : "Lire la suite"}</Text>
                </Pressable>
              ) : null}
            </View>
          ) : null}

          <Pressable
            accessibilityRole="button"
            onPress={() => router.push(`/signaler?type=listing&id=${fiche.id}` as never)}
            style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, padding: sp[3] }}
          >
            <Flag size={14} color={colors.textMuted} />
            <Text variante="legende" muted>Signaler cette annonce</Text>
          </Pressable>
        </View>
      </ScrollView>

      {/* Actions fixes */}
      <View style={{ flexDirection: "row", gap: sp[3], padding: sp[4], borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.surface }}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Me prévenir pour des chambres similaires"
          onPress={() => router.push("/nouvelle-alerte")}
          style={({ pressed }) => ({ width: 52, minHeight: 48, borderRadius: rayon.field, borderWidth: 1.5, borderColor: colors.border, backgroundColor: pressed ? colors.divider : colors.surface, alignItems: "center", justifyContent: "center" })}
        >
          <Bell size={20} color={colors.night} />
        </Pressable>
        <Button titre="Contacter le gérant" style={{ flex: 1 }} onPress={contacter} disabled={fiche.status !== "published"} />
      </View>
    </SafeAreaView>
  );
}
