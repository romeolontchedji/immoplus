import { useEffect, useRef } from "react";
import { Pressable, ScrollView, Share, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Image } from "expo-image";
import { isApiError } from "@/api/errors";
import { fcfa } from "@/lib/format";
import { messageErreur, t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { CIBLE_MIN, colors, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Badge } from "@/ui/components/Card";
import { ErrorState, QueryState } from "@/ui/components/States";
import { Text } from "@/ui/components/Text";
import { OfflineBanner } from "@/ui/components/States";
import { useFiche, useCompterVue, useBasculerFavori } from "./queries";
import { SafeAreaView } from "react-native-safe-area-context";

const EQUIP_LABELS: Record<string, string> = {
  has_private_bathroom: "Douche interne",
  has_water: "Eau",
  has_electricity: "Eau + électricité",
  has_internet: "Internet",
  is_fenced: "Cour clôturée",
  has_well: "Forage",
  has_tiled_floor: "Carrelé",
};

/**
 * Fiche d'annonce (EF-REC-06 à EF-REC-10).
 * Conforme à la maquette « Mobile · Détail chambre@1x.png » :
 * - Vidéo/photo plein écran fond bleu nuit dégradé en haut (pas de barre de navigation)
 * - Flèche retour (cercle blanc) en haut à gauche, icône favori (cercle blanc) en haut à droite
 * - Feuille blanche arrondie qui remonte sur l'image (borderTopLeftRadius + borderTopRightRadius 28)
 * - Titre + prix bleu cobalt sur la même ligne
 * - Sous-titre muted : distance + statut
 * - Chips équipements en pilule (contour, fond blanc)
 * - Carte gérant : avatar initiales + badge "Vérifié" vert + délai de réponse
 * - Footer fixe 2 boutons : "Me prévenir" (secondaire) + "Contacter le gérant" (primaire)
 */
export function FicheScreen() {
  const { c } = useTheme();
  const router = useRouter();
  const { ident } = useLocalSearchParams<{ ident: string }>();
  const { etat } = useSession();
  const requete = useFiche(ident);
  const compterVue = useCompterVue();
  const basculerFavori = useBasculerFavori();

  // Compter la vue une seule fois
  useEffect(() => {
    if (ident) compterVue.mutate(ident);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ident]);

  if (requete.isError) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }}>
        <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} />
      </SafeAreaView>
    );
  }

  if (!requete.data) {
    // Squelette : fond bleu nuit pendant le chargement
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.night }}>
        <View style={{ flex: 1, backgroundColor: colors.night }} />
      </SafeAreaView>
    );
  }

  const fiche = requete.data;
  const initiales = fiche.gerant.full_name
    .split(" ")
    .slice(0, 2)
    .map((m: string) => m[0]?.toUpperCase() ?? "")
    .join("");

  const equipements = Object.entries(EQUIP_LABELS)
    .filter(([cle]) => (fiche as unknown as Record<string, unknown>)[cle] === true)
    .map(([, label]) => label);

  const partager = async () => {
    const url = `https://${process.env.EXPO_PUBLIC_WEB_HOST ?? "logeo.example"}/annonces/${fiche.slug ?? fiche.id}`;
    await Share.share({ message: `${fiche.title} — ${fcfa(fiche.rent_amount)}/mois sur Logeo\n${url}` });
  };

  const basculer = () => {
    if (etat.statut !== "connecte") { router.push("/connexion"); return; }
    basculerFavori.mutate({ id: fiche.id, ident: fiche.slug ?? fiche.id, actif: !fiche.is_favorite });
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }} edges={["bottom"]}>
      <OfflineBanner />
      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ flexGrow: 1 }} scrollEventThrottle={16} bounces={false}>

        {/* ── Zone média plein écran bleu nuit ── */}
        <View style={{ height: 300, backgroundColor: colors.night, justifyContent: "center", alignItems: "center" }}>
          {fiche.cover_url ? (
            <Image
              source={{ uri: fiche.cover_url }}
              style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
              contentFit="cover"
              accessibilityIgnoresInvertColors
            />
          ) : null}
          {/* Dégradé bleu nuit semi-transparent sur l'image */}
          <View
            style={{
              position: "absolute",
              top: 0, left: 0, right: 0, bottom: 0,
              backgroundColor: fiche.cover_url ? "rgba(15,27,61,0.35)" : colors.night,
            }}
          />
          {/* Bouton lecture vidéo */}
          {fiche.has_video ? (
            <View
              style={{
                width: 60,
                height: 60,
                borderRadius: 30,
                backgroundColor: "rgba(255,255,255,0.92)",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {/* Triangle play */}
              <View style={{ width: 0, height: 0, borderTopWidth: 10, borderBottomWidth: 10, borderLeftWidth: 18, borderTopColor: "transparent", borderBottomColor: "transparent", borderLeftColor: colors.blue, marginLeft: 4 }} />
            </View>
          ) : null}
          {/* Durée vidéo en bas à droite */}
          {fiche.video_duration_s ? (
            <View style={{ position: "absolute", bottom: sp[3], right: sp[3], backgroundColor: "rgba(0,0,0,0.55)", borderRadius: 6, paddingHorizontal: sp[2], paddingVertical: 2 }}>
              <Text variante="legende" couleur="#FFFFFF">{`0:${fiche.video_duration_s.toString().padStart(2, "0")}`}</Text>
            </View>
          ) : null}
          {/* Badge Vérifié en haut à gauche */}
          {fiche.gerant?.verified ? (
            <View style={{ position: "absolute", top: sp[4], left: sp[4], flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: "#12805C", borderRadius: 999, paddingHorizontal: sp[3], paddingVertical: 4 }}>
              <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: "#FFFFFF" }} />
              <Text variante="legende" couleur="#FFFFFF" style={{ fontWeight: "700" }}>Vérifié</Text>
            </View>
          ) : null}
        </View>

        {/* ── Boutons flèche retour + favori superposés ── */}
        <View style={{ position: "absolute", top: 48, left: 0, right: 0, flexDirection: "row", justifyContent: "space-between", paddingHorizontal: sp[4] }}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={t.commun.retour}
            onPress={() => router.back()}
            style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: "rgba(255,255,255,0.92)", alignItems: "center", justifyContent: "center" }}
          >
            <Text style={{ fontSize: 20, lineHeight: 24, color: colors.night }}>←</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={fiche.is_favorite ? "Retirer des favoris" : "Ajouter aux favoris"}
            onPress={basculer}
            style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: "rgba(255,255,255,0.92)", alignItems: "center", justifyContent: "center" }}
          >
            {/* Cœur : plein si favori */}
            <Text style={{ fontSize: 18, color: fiche.is_favorite ? "#D13B3B" : colors.sable300 }}>
              {fiche.is_favorite ? "♥" : "♡"}
            </Text>
          </Pressable>
        </View>

        {/* ── Feuille blanche avec coin arrondi qui remonte sur l'image ── */}
        <View
          style={{
            backgroundColor: c.bg,
            borderTopLeftRadius: 28,
            borderTopRightRadius: 28,
            marginTop: -28,
            padding: sp[4],
            gap: sp[4],
            flex: 1,
          }}
        >
          {/* Titre + prix */}
          <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: sp[3] }}>
            <Text variante="titreSection" style={{ flex: 1 }}>{fiche.title}</Text>
            <View style={{ alignItems: "flex-end" }}>
              <Text variante="prix" couleur={c.primary}>{fcfa(fiche.rent_amount)} F</Text>
              <Text variante="legende" muted>/ mois</Text>
            </View>
          </View>

          {/* Sous-titre : distance + disponibilité */}
          <Text variante="legende" muted>
            {fiche.district?.name ? `${fiche.district.name} · ` : ""}
            {fiche.status === "published" ? "Disponible maintenant" : t.statutAnnonce[fiche.status] ?? fiche.status}
          </Text>

          {fiche.last_confirmed_at ? (
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: "#0D9488" }} />
              <Text variante="legende" couleur="#0D9488" style={{ fontWeight: "600" }}>
                Disponibilité confirmée récemment
              </Text>
            </View>
          ) : null}

          {/* Chips équipements en pilule (contour, fond blanc) */}
          {equipements.length ? (
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
              {equipements.map((eq) => (
                <View
                  key={eq}
                  style={{
                    paddingHorizontal: sp[3],
                    paddingVertical: sp[2],
                    borderRadius: rayon.pilule,
                    borderWidth: 1,
                    borderColor: c.border,
                    backgroundColor: c.surface,
                  }}
                >
                  <Text variante="legende">{eq}</Text>
                </View>
              ))}
              {fiche.deposit_months ? (
                <View style={{ paddingHorizontal: sp[3], paddingVertical: sp[2], borderRadius: rayon.pilule, borderWidth: 1, borderColor: c.border, backgroundColor: c.surface }}>
                  <Text variante="legende">Caution {fiche.deposit_months} mois</Text>
                </View>
              ) : null}
            </View>
          ) : null}

          {/* Carte gérant (conforme maquette) */}
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: sp[3],
              padding: sp[4],
              backgroundColor: c.surface,
              borderRadius: rayon.card,
              borderWidth: 1,
              borderColor: c.border,
            }}
          >
            {/* Avatar initiales */}
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: c.primarySoft, alignItems: "center", justifyContent: "center" }}>
              <Text variante="legende" couleur={c.primary} style={{ fontWeight: "800" }}>{initiales}</Text>
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
                <Text variante="corpsGras">{fiche.gerant.full_name}</Text>
                {fiche.gerant.verified ? (
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: "#DDF3EA", borderRadius: 999, paddingHorizontal: sp[2], paddingVertical: 2 }}>
                    <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: "#12805C" }} />
                    <Text variante="legende" couleur="#0C6B4A" style={{ fontWeight: "700" }}>Vérifié</Text>
                  </View>
                ) : null}
              </View>
              <Text variante="legende" muted>
                Gérant · {fiche.gerant.avg_response_h != null ? `répond en moins de ${fiche.gerant.avg_response_h} h` : "Gérant"}
              </Text>
            </View>
          </View>

          {/* Description */}
          {fiche.description_text ? (
            <View>
              <Text variante="label" style={{ marginBottom: sp[2] }}>Description</Text>
              <Text muted numberOfLines={6}>{fiche.description_text}</Text>
            </View>
          ) : null}

          {/* Signaler */}
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push(`/signaler?type=listing&id=${fiche.id}` as never)}
            style={{ alignItems: "center", padding: sp[2] }}
          >
            <Text variante="legende" muted>Signaler cette annonce</Text>
          </Pressable>
        </View>
      </ScrollView>

      {/* ── Footer 2 boutons : "Me prévenir" + "Contacter le gérant" ── */}
      <View
        style={{
          flexDirection: "row",
          gap: sp[3],
          padding: sp[4],
          borderTopWidth: 1,
          borderTopColor: c.border,
          backgroundColor: c.surface,
        }}
      >
        <Button
          titre="Me prévenir"
          variante="secondaire"
          style={{ flex: 1 }}
          onPress={() => router.push("/nouvelle-alerte")}
        />
        <Button
          titre="Contacter le gérant"
          style={{ flex: 2 }}
          onPress={() => {
            if (etat.statut !== "connecte") { router.push("/connexion"); return; }
            router.push(`/conversation/nouvelle?listing=${fiche.id}` as never);
          }}
        />
      </View>
    </SafeAreaView>
  );
}
