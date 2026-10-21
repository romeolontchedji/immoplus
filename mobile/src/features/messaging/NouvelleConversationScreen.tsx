import { useRef, useState } from "react";
import { Alert, Pressable, ScrollView, TextInput, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Image } from "expo-image";
import { BadgeCheck, ShieldAlert, X } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/api/client";
import { isApiError } from "@/api/errors";
import { qk } from "@/api/keys";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { useFiche, type Fiche } from "@/features/listings/queries";
import { messageErreur, t } from "@/i18n/fr";
import { francs } from "@/lib/format";
import { urlMedia } from "@/lib/media";
import { newId } from "@/lib/uuid";
import { proposerNotifications } from "@/features/notifications/DemandeNotifications";
import { useSession } from "@/state/session";
import { Button } from "@/ui/components/Button";
import { Chip } from "@/ui/components/Chip";
import { Screen } from "@/ui/components/Screen";
import { Skeleton } from "@/ui/components/Skeleton";
import { ErrorState, EmptyState } from "@/ui/components/States";
import { Text } from "@/ui/components/Text";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";

const LONGUEUR_MAX = 2000;
const REPONSES_RAPIDES = ["Est-elle toujours libre ?", "Puis-je visiter aujourd'hui ?", "Que comprend le loyer ?"];

/** Message d'ouverture suggéré (COPYWRITING §6 Conversation) : « Bonjour, la {type} à {quartier} est-elle toujours libre ? » */
function messageSuggere(f: Fiche): string {
  const type = (f.room_type_label || "chambre").toLowerCase();
  return `Bonjour, la ${type} à ${f.district.name} est-elle toujours libre ?`;
}

function texteErreur(e: unknown): string {
  if (!isApiError(e)) return messageErreur("network");
    if (e.code === "wrong_audience") return "Seuls les comptes locataires peuvent écrire à un gérant.";
  if (e.code === "forbidden") return e.message;
  return e.field("body") ?? messageErreur(e.code, e.message);
}

/**
 * « Écrire au gérant » (EF-MSG-01, EF-MSG-12) : carte de la chambre, message d'ouverture prérempli et modifiable,
 * réponses rapides, rappel de sécurité, puis ouverture de la conversation. Le serveur retrouve la conversation si elle
 * existe déjà ; `client_msg_id` reste le même pour un même texte, donc une nouvelle tentative ne crée jamais de doublon.
 */
export function NouvelleConversationScreen() {
  const { listing } = useLocalSearchParams<{ listing?: string }>();
  const { etat } = useSession();
  if (etat.statut !== "connecte") {
    return (
      <Screen scroll>
        <AuthRequired />
      </Screen>
    );
  }
  return <Formulaire annonceId={listing} />;
}

function Formulaire({ annonceId }: { annonceId?: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const { role } = useSession();
  const fiche = useFiche(annonceId);
  const [texte, setTexte] = useState<string | null>(null);
  const idMessage = useRef<{ corps: string; id: string } | null>(null);

  const ouvrir = useMutation({
    mutationFn: async (corps: string) => {
      if (idMessage.current?.corps !== corps) idMessage.current = { corps, id: newId() };
      return unwrap(api.POST("/v1/conversations", { body: { listing_id: annonceId as string, body: corps, client_msg_id: idMessage.current.id } }));
    },
    onSuccess: (r) => {
      void qc.invalidateQueries({ queryKey: qk.conversations });
      router.replace({ pathname: "/conversation/[id]", params: { id: r.conversation.id } });
      if (r.warning) Alert.alert("Message envoyé", r.warning);
      else void proposerNotifications("message"); // le bon moment : on attend maintenant une réponse
    },
  });

  const fermer = () => (router.canGoBack() ? router.back() : router.replace("/"));

  if (role === "gerant") {
    return (
      <Screen scroll>
        <EmptyState titre="Réservé aux locataires" texte="Les gérants répondent aux locataires depuis leurs messages." action={t.commun.fermer} onAction={fermer} />
      </Screen>
    );
  }
  if (fiche.isError) return <Screen><ErrorState erreur={fiche.error} onRetry={() => void fiche.refetch()} /></Screen>;

  const f = fiche.data;
  const valeur = texte ?? (f ? messageSuggere(f) : "");
  const vide = valeur.trim().length === 0;
  const indisponible = !!f && f.status !== "published";
  const couverture = f?.media.find((m) => m.is_cover) ?? f?.media[0];
  const image = urlMedia(couverture ? (couverture.kind === "video" ? couverture.poster_url : (couverture.thumb_url ?? couverture.url)) : null);

  return (
    <Screen
      footer={
        <Button
          titre="Envoyer au gérant"
          chargement={ouvrir.isPending}
          disabled={!f || vide || indisponible}
          onPress={() => ouvrir.mutate(valeur.trim())}
        />
      }
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: sp[3] }}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t.commun.fermer}
          onPress={fermer}
          style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center" }}
        >
          <X size={18} color={colors.night} />
        </Pressable>
        <Text variante="titreSection">Écrire au gérant</Text>
      </View>

      <ScrollView contentContainerStyle={{ gap: sp[4], paddingBottom: sp[4] }} keyboardShouldPersistTaps="handled">
        {f ? (
          <View style={{ flexDirection: "row", gap: sp[3], padding: sp[3], backgroundColor: colors.surface, borderRadius: rayon.card, ...ombre.card }}>
            <View style={{ width: 64, height: 64, borderRadius: 14, overflow: "hidden", backgroundColor: colors.night }}>
              <Image
                source={image ? { uri: image } : require("../../../assets/illustration-chambres.svg")}
                style={{ width: "100%", height: "100%" }}
                contentFit="cover"
                accessibilityIgnoresInvertColors
              />
            </View>
            <View style={{ flex: 1, gap: 2, justifyContent: "center" }}>
              <Text variante="corpsGras" numberOfLines={1}>{f.title}</Text>
              <Text variante="legende" muted numberOfLines={1}>{`${f.district.name} · ${francs(f.rent_amount)}/mois`}</Text>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
                {f.gerant?.verified ? <BadgeCheck size={14} color={colors.successText} /> : null}
                <Text variante="legende" couleur={f.gerant?.verified ? colors.successText : colors.textMuted} style={{ fontWeight: "700" }}>
                  {f.gerant?.name ?? "Gérant"}{f.gerant?.verified ? " · vérifié" : ""}
                </Text>
              </View>
            </View>
          </View>
        ) : (
          <Skeleton hauteur={88} />
        )}

        {indisponible ? (
          <Text variante="corpsGras" couleur={colors.warning}>{messageErreur("listing_unavailable")}</Text>
        ) : null}

        <View style={{ gap: sp[2] }}>
          <Text variante="label" muted>Ton message</Text>
          <TextInput
            value={valeur}
            onChangeText={(v) => setTexte(v.slice(0, LONGUEUR_MAX))}
            multiline
            textAlignVertical="top"
            placeholder="Écris un message…"
            placeholderTextColor={colors.textMuted}
            accessibilityLabel="Ton message au gérant"
            style={{ minHeight: 120, padding: sp[4], borderRadius: rayon.field, borderWidth: 1.5, borderColor: ouvrir.error ? colors.danger : colors.border, backgroundColor: colors.surface, fontSize: 16, lineHeight: 22, color: colors.night }}
          />
          <Text variante="legende" muted style={{ textAlign: "right" }}>{`${valeur.length} / ${LONGUEUR_MAX}`}</Text>
        </View>

        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          {REPONSES_RAPIDES.map((r) => (
            <Chip key={r} titre={r} actif={valeur.includes(r)} onPress={() => setTexte(valeur.includes(r) ? valeur.replace(r, "").replace(/\s{2,}/g, " ").trim() : `${valeur.trim()} ${r}`.trim())} />
          ))}
        </View>

        {ouvrir.error ? (
          <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">{texteErreur(ouvrir.error)}</Text>
        ) : null}

        <View style={{ flexDirection: "row", gap: sp[3], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.warningBg }}>
          <ShieldAlert size={20} color={colors.warningText} />
          <Text variante="legende" couleur={colors.warningText} style={{ flex: 1, lineHeight: 19 }}>
            Ne paie jamais avant d’avoir visité. Tu choisis de partager ton numéro ou non ; signale tout message suspect.
          </Text>
        </View>
      </ScrollView>
    </Screen>
  );
}
