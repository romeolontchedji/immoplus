import { useEffect, useRef, useState } from "react";
import { FlatList, Pressable, ScrollView, Share, TextInput, useWindowDimensions, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Image } from "expo-image";
import { useVideoPlayer, VideoView } from "expo-video";
import {
  ArrowLeft, BadgeCheck, Bell, CalendarDays, ChevronLeft, ChevronRight, Droplet, Fence, Flag, Heart, MapPin, Play, Share2,
  ShowerHead, Star, Utensils, Zap, type LucideIcon,
} from "lucide-react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { isApiError } from "@/api/errors";
import { WEB_HOST } from "@/config/env";
import { dateCourte, distance, francs } from "@/lib/format";
import { urlMedia } from "@/lib/media";
import { messageErreur, t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { ErrorState, OfflineBanner } from "@/ui/components/States";
import { Skeleton } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { ListingCard } from "@/ui/components/ListingCard";
import { noterConsultation } from "./consultees";
import {
  useAvis, useBasculerFavori, useCompterVue, useDemarrerConversation, useFiche, useMonAvis, useSimilaires, type Fiche,
} from "./queries";

type Media = Fiche["media"][number];

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

function BoutonRond({ libelle, onPress, children, desactive }: { libelle: string; onPress: () => void; children: React.ReactNode; desactive?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={libelle}
      accessibilityState={{ disabled: !!desactive }}
      disabled={desactive}
      onPress={onPress}
      hitSlop={6}
      style={({ pressed }) => ({ width: 42, height: 42, borderRadius: 21, opacity: desactive ? 0 : 1, backgroundColor: pressed ? colors.divider : colors.white, alignItems: "center", justifyContent: "center", ...ombre.card })}
    >
      {children}
    </Pressable>
  );
}

/**
 * Galerie (plan v3, B1) : une diapositive à la fois, toutes au même format (vidéo d'abord, puis les photos). On glisse du
 * doigt ou on appuie sur les flèches ; le compteur suit. La vidéo se lit sur place.
 */
function Galerie({ medias, hauteur }: { medias: Media[]; hauteur: number }) {
  const { width } = useWindowDimensions();
  const liste = useRef<FlatList<Media>>(null);
  const [index, setIndex] = useState(0);
  const [lecture, setLecture] = useState<string | null>(null);
  const aller = (i: number) => {
    const cible = Math.max(0, Math.min(medias.length - 1, i));
    setLecture(null);
    liste.current?.scrollToIndex({ index: cible, animated: true });
    setIndex(cible);
  };
  if (!medias.length) {
    return <Image source={require("../../../assets/illustration-chambres.svg")} style={{ width, height: hauteur }} contentFit="cover" />;
  }
  return (
    <View style={{ height: hauteur, backgroundColor: colors.night }}>
      <FlatList
        ref={liste}
        data={medias}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        keyExtractor={(m) => m.id}
        getItemLayout={(_d, i) => ({ length: width, offset: width * i, index: i })}
        onMomentumScrollEnd={(e) => {
          setIndex(Math.round(e.nativeEvent.contentOffset.x / width));
          setLecture(null);
        }}
        renderItem={({ item }) => (
          <View style={{ width, height: hauteur, alignItems: "center", justifyContent: "center" }}>
            {item.kind === "video" && lecture === item.id ? (
              <LecteurVideo uri={urlMedia(item.playback_url) ?? ""} />
            ) : (
              <>
                <Image source={imageDe(item) ? { uri: imageDe(item) as string } : undefined} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }} contentFit="cover" transition={150} accessibilityIgnoresInvertColors />
                {item.kind === "video" ? (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Lire la vidéo de la chambre"
                    onPress={() => setLecture(item.id)}
                    style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: colors.white, alignItems: "center", justifyContent: "center", ...ombre.pop }}
                  >
                    <Play size={26} color={colors.primary} fill={colors.primary} style={{ marginLeft: 4 }} />
                  </Pressable>
                ) : null}
              </>
            )}
          </View>
        )}
      />
      {medias.length > 1 ? (
        <>
          <View style={{ position: "absolute", top: "50%", left: sp[3], marginTop: -21 }}>
            <BoutonRond libelle="Photo précédente" onPress={() => aller(index - 1)} desactive={index === 0}><ChevronLeft size={22} color={colors.night} /></BoutonRond>
          </View>
          <View style={{ position: "absolute", top: "50%", right: sp[3], marginTop: -21 }}>
            <BoutonRond libelle="Photo suivante" onPress={() => aller(index + 1)} desactive={index === medias.length - 1}><ChevronRight size={22} color={colors.night} /></BoutonRond>
          </View>
          <View style={{ position: "absolute", bottom: sp[10], right: sp[4], backgroundColor: "rgba(15,27,61,0.65)", borderRadius: rayon.pilule, paddingHorizontal: sp[3], paddingVertical: 4 }}>
            <Text style={{ color: colors.white, fontSize: 13, fontWeight: "800" }} accessibilityLiveRegion="polite">{`${index + 1} / ${medias.length}`}</Text>
          </View>
        </>
      ) : null}
    </View>
  );
}

function Equipement({ Icone, libelle, valeur }: { Icone: LucideIcon; libelle: string; valeur: string }) {
  return (
    <View style={{ width: "48%", flexDirection: "row", alignItems: "center", gap: sp[2], padding: sp[3], borderRadius: rayon.field, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.divider }}>
      <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center" }}>
        <Icone size={18} color={colors.primary} />
      </View>
      <View style={{ flex: 1 }}>
        <Text variante="legende" muted>{libelle}</Text>
        <Text style={{ fontSize: 14, fontWeight: "700", color: colors.night }}>{valeur}</Text>
      </View>
    </View>
  );
}

function Etoiles({ note, taille = 14 }: { note: number; taille?: number }) {
  return (
    <View style={{ flexDirection: "row", gap: 2 }} accessibilityLabel={`${note} sur 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} size={taille} color={n <= note ? colors.sunHover : colors.border} fill={n <= note ? colors.sunHover : colors.border} />
      ))}
    </View>
  );
}

/** Formulaire d'avis : part des valeurs déjà données (modifier) ou vides (première fois). */
function FormulaireAvis({ ident, initial }: { ident: string; initial: { rating: number; comment: string } | null }) {
  const { donner, retirer } = useMonAvis(ident);
  const [note, setNote] = useState(initial?.rating ?? 0);
  const [commentaire, setCommentaire] = useState(initial?.comment ?? "");
  const erreur = donner.error ?? retirer.error;
  return (
    <View style={{ gap: sp[3], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.blueSoft }}>
      <Text variante="corpsGras">{initial ? "Modifier ton avis" : "Ta note"}</Text>
      <View style={{ flexDirection: "row", gap: sp[2] }}>
        {[1, 2, 3, 4, 5].map((n) => (
          <Pressable key={n} accessibilityRole="radio" accessibilityState={{ checked: note === n }} accessibilityLabel={`${n} sur 5`} onPress={() => setNote(n)} hitSlop={4}>
            <Star size={32} color={n <= note ? colors.sunHover : colors.border} fill={n <= note ? colors.sunHover : colors.border} />
          </Pressable>
        ))}
      </View>
      <TextInput
        value={commentaire}
        onChangeText={setCommentaire}
        maxLength={600}
        multiline
        placeholder="Propreté, calme, eau, électricité, accueil du gérant…"
        placeholderTextColor={colors.textMuted}
        accessibilityLabel="Ton commentaire (facultatif)"
        style={{ minHeight: 80, textAlignVertical: "top", backgroundColor: colors.surface, borderRadius: rayon.field, borderWidth: 1, borderColor: colors.border, padding: sp[3], fontSize: 15, color: colors.night }}
      />
      {erreur ? <Text variante="legende" couleur={colors.danger}>{isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.commun.erreurGenerique}</Text> : null}
      {donner.isSuccess ? <Text variante="legende" couleur={colors.success}>Merci, ton avis est publié.</Text> : null}
      <Button titre={initial ? "Mettre à jour mon avis" : "Publier mon avis"} disabled={note === 0} chargement={donner.isPending} onPress={() => donner.mutate({ rating: note, comment: commentaire })} />
      {initial ? <Button titre="Retirer mon avis" variante="fantome" chargement={retirer.isPending} onPress={() => retirer.mutate()} /> : null}
    </View>
  );
}

/** Avis des locataires (plan v3, G) : moyenne, liste, et formulaire pour qui a vraiment échangé avec le gérant. */
function Avis({ ident }: { ident: string }) {
  const { data } = useAvis(ident);
  if (!data) return null;
  const mien = data.my_review ? { rating: Number(data.my_review.rating) || 0, comment: String(data.my_review.comment ?? "") } : null;
  return (
    <View style={{ gap: sp[3] }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Text variante="label" muted>Avis des locataires</Text>
        {data.summary.count ? <Text variante="corpsGras">{`★ ${Number(data.summary.average).toFixed(1).replace(".", ",")} · ${data.summary.count} avis`}</Text> : null}
      </View>
      {data.can_review ? <FormulaireAvis key={mien ? `${mien.rating}-${mien.comment}` : "nouveau"} ident={ident} initial={mien} /> : null}
      {data.items.length ? (
        data.items.map((a) => (
          <View key={a.id} style={{ gap: sp[1], paddingBottom: sp[3], borderBottomWidth: 1, borderBottomColor: colors.divider }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
              <Text variante="corpsGras">{a.author_name}</Text>
              <Etoiles note={a.rating} />
              <Text variante="legende" muted>{dateCourte(a.created_at)}</Text>
            </View>
            {a.comment ? <Text>{a.comment}</Text> : null}
          </View>
        ))
      ) : (
        <Text muted>Aucun avis pour l’instant.</Text>
      )}
    </View>
  );
}

/** Chambres similaires en bandeau horizontal (plan v2, S3). */
function Similaires({ ident }: { ident: string }) {
  const router = useRouter();
  const { data } = useSimilaires(ident);
  const { width } = useWindowDimensions();
  if (!data?.length) return null;
  return (
    <View style={{ gap: sp[2] }}>
      <Text variante="label" muted>Chambres similaires</Text>
      <FlatList
        horizontal
        data={data}
        keyExtractor={(c) => c.id}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: sp[3] }}
        renderItem={({ item }) => (
          <View style={{ width: Math.min(280, width * 0.75) }}>
            <ListingCard annonce={item} onPress={() => router.push({ pathname: "/annonces/[ident]", params: { ident: item.slug } })} />
          </View>
        )}
      />
    </View>
  );
}

/**
 * Fiche d'annonce (plan v3) : quartier d'abord, galerie à diapositives de même taille, prix (« à débattre »), note des
 * avis, équipements, gérant (son profil d'un appui), conditions, autres détails, avis, chambres similaires. « Contacter »
 * ouvre directement la discussion, sans message imposé.
 */
export function FicheScreen() {
  const router = useRouter();
  const haut = useSafeAreaInsets().top;
  const { ident } = useLocalSearchParams<{ ident: string }>();
  const { etat } = useSession();
  const requete = useFiche(ident);
  const compterVue = useCompterVue();
  const basculerFavori = useBasculerFavori();
  const demarrer = useDemarrerConversation();

  useEffect(() => {
    if (ident) compterVue.mutate(ident);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ident]);

  const chargee = requete.data;
  useEffect(() => {
    if (!chargee) return;
    const m = chargee.media ?? [];
    noterConsultation({
      slug: chargee.slug,
      title: chargee.title,
      rent_amount: chargee.rent_amount,
      district: chargee.district?.name ?? "",
      image: imageDe(m.find((x) => x.is_cover) ?? m[0]),
    });
  }, [chargee]);

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
  const medias = [...(fiche.media ?? [])].sort((a, b) => (a.kind === "video" ? -1 : b.kind === "video" ? 1 : 0));
  const lien = `https://${WEB_HOST}/annonces/${fiche.slug}`;

  const basculer = () => {
    if (etat.statut !== "connecte") return router.push("/connexion");
    basculerFavori.mutate({ id: fiche.id, ident: fiche.slug, actif: !fiche.is_favorite });
  };
  const contacter = () => {
    if (etat.statut !== "connecte") return router.push("/connexion");
    demarrer.mutate(fiche.id, { onSuccess: (c) => router.push({ pathname: "/conversation/[id]", params: { id: c.id } }) });
  };

  const delai = delaiReponse(fiche.gerant?.median_response_min);
  const details = fiche.description_md?.trim();
  const note = fiche.reviews;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["bottom"]}>
      <OfflineBanner />
      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ flexGrow: 1 }} bounces={false}>
        <Galerie medias={medias} hauteur={300 + haut} />

        {/* Boutons superposés : retour, partage, favori toujours en haut (plan v3, B2) */}
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

        <View style={{ backgroundColor: colors.bg, borderTopLeftRadius: rayon.sheet, borderTopRightRadius: rayon.sheet, marginTop: -28, padding: sp[4], paddingTop: sp[5], gap: sp[5], flex: 1 }}>
          <View style={{ gap: sp[2] }}>
            {/* Le quartier d'abord (plan v3, B2) */}
            <View style={{ alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.primary, borderRadius: rayon.pilule, paddingHorizontal: sp[3], paddingVertical: 6 }}>
              <MapPin size={16} color={colors.white} />
              <Text style={{ color: colors.white, fontWeight: "800", fontSize: 15 }}>{fiche.district?.name}</Text>
            </View>
            <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: sp[3] }}>
              <View style={{ flex: 1, gap: 4 }}>
                <Text variante="titreSection">{fiche.title}</Text>
                <Text variante="legende" muted>
                  {[fiche.room_type_label, fiche.distance_m != null ? `${distance(fiche.distance_m)} de l'UP` : null, fiche.landmark_text].filter(Boolean).join(" · ")}
                </Text>
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={{ fontSize: 22, fontWeight: "800", color: colors.primary }}>{francs(fiche.rent_amount)}</Text>
                <Text variante="legende" muted>par mois</Text>
                {fiche.rent_negotiable ? (
                  <View style={{ marginTop: 4, backgroundColor: colors.warningBg, borderRadius: rayon.pilule, paddingHorizontal: sp[2], paddingVertical: 2 }}>
                    <Text style={{ fontSize: 12, fontWeight: "800", color: colors.warning }}>À débattre</Text>
                  </View>
                ) : null}
              </View>
            </View>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              {note.count ? (
                <>
                  <Star size={16} color={colors.sunHover} fill={colors.sunHover} />
                  <Text variante="corpsGras">{Number(note.average).toFixed(1).replace(".", ",")}</Text>
                  <Text variante="legende" muted>{`· ${note.count} avis`}</Text>
                </>
              ) : (
                <Text variante="legende" muted>Pas encore d’avis</Text>
              )}
            </View>
            {fiche.status !== "published" ? <Text variante="corpsGras" couleur={colors.warning}>{t.statutAnnonce[fiche.status] ?? fiche.status}</Text> : null}
          </View>

          {/* Équipements (plan v3, B4) */}
          <View style={{ gap: sp[2] }}>
            <Text variante="label" muted>Équipements</Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", rowGap: sp[2] }}>
              <Equipement Icone={Zap} libelle="Électricité" valeur={fiche.electricity_label || "Non précisé"} />
              <Equipement Icone={Droplet} libelle="Eau" valeur={fiche.water_label || "Non précisé"} />
              <Equipement Icone={Utensils} libelle="Cuisine" valeur={fiche.kitchen_label || "Non précisé"} />
              <Equipement Icone={ShowerHead} libelle="Douche et WC" valeur={fiche.has_private_bathroom ? "Internes" : "Partagés"} />
              <Equipement Icone={Fence} libelle="Cour" valeur={fiche.is_fenced ? "Clôturée" : "Ouverte"} />
              <Equipement Icone={CalendarDays} libelle="Disponible" valeur={fiche.available_from ? dateCourte(fiche.available_from) : "Maintenant"} />
            </View>
          </View>

          {/* Gérant : son profil et ses chambres d'un appui (plan v3, F) */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Voir le profil de ${fiche.gerant?.name ?? "ce gérant"}`}
            onPress={() => router.push({ pathname: "/gerant/[id]", params: { id: String(fiche.gerant.id) } })}
            style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: sp[3], padding: sp[4], backgroundColor: pressed ? colors.divider : colors.surface, borderRadius: rayon.card, borderWidth: 1, borderColor: colors.border })}
          >
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
              <Text variante="legende" muted>{delai ? `${delai} · voir son profil` : "Voir son profil et ses chambres"}</Text>
            </View>
            <ChevronRight size={20} color={colors.textMuted} />
          </Pressable>

          <View>
            <Text variante="label" muted style={{ marginBottom: sp[1] }}>Conditions</Text>
            <Ligne libelle="Loyer" valeur={`${francs(fiche.rent_amount)} / mois${fiche.rent_negotiable ? " (à débattre)" : ""}`} />
            {fiche.deposit_months ? <Ligne libelle="Caution" valeur={`${fiche.deposit_months} mois`} /> : null}
            {fiche.advance_months ? <Ligne libelle="Avance" valeur={`${fiche.advance_months} mois`} /> : null}
            <Ligne libelle="Frais de démarcheur" valeur={fiche.agent_fee_amount ? francs(fiche.agent_fee_amount) : "Aucun"} />
          </View>

          {details ? (
            <View style={{ gap: sp[2] }}>
              <Text variante="label" muted>Autres détails</Text>
              <Text style={{ lineHeight: 23 }}>{details}</Text>
            </View>
          ) : null}

          <Avis ident={fiche.slug} />

          <Similaires ident={fiche.slug} />

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

      {/* Actions fixes : un seul bouton pour entrer dans la discussion (plan v3, B6) */}
      <View style={{ gap: sp[2], padding: sp[4], borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.surface }}>
        {demarrer.error ? (
          <Text variante="legende" couleur={colors.danger}>{isApiError(demarrer.error) ? messageErreur(demarrer.error.code, demarrer.error.message) : t.commun.erreurGenerique}</Text>
        ) : null}
        <View style={{ flexDirection: "row", gap: sp[3] }}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Créer une alerte pour des chambres semblables"
            onPress={() => router.push("/nouvelle-alerte")}
            style={({ pressed }) => ({ width: 52, minHeight: 48, borderRadius: rayon.field, borderWidth: 1.5, borderColor: colors.border, backgroundColor: pressed ? colors.divider : colors.surface, alignItems: "center", justifyContent: "center" })}
          >
            <Bell size={20} color={colors.night} />
          </Pressable>
          <Button titre="Contacter le gérant" style={{ flex: 1 }} onPress={contacter} chargement={demarrer.isPending} disabled={fiche.status !== "published"} />
        </View>
      </View>
    </SafeAreaView>
  );
}
