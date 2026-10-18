import { useEffect, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Pressable, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ArrowLeft, BadgeCheck, BellOff, EllipsisVertical, Send } from "lucide-react-native";
import { Image } from "expo-image";
import { isApiError } from "@/api/errors";
import { francs, heure } from "@/lib/format";
import { urlMedia } from "@/lib/media";
import { useFiche } from "@/features/listings/queries";
import { messageErreur } from "@/i18n/fr";
import { useConversationFocus } from "@/realtime/RealtimeProvider";
import { useSession } from "@/state/session";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { outbox } from "@/storage/outbox";
import { ErrorState } from "@/ui/components/States";
import { Skeleton } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { MenuConversation } from "./MenuConversation";
import {
  useConversation,
  useEnvoyerMessage,
  useLignes,
  useLireConversation,
  useMessages,
  useReprendreEnvoi,
} from "./queries";

/**
 * Conversation conforme à la maquette Mobile · Conversation@1x.png :
 * - En-tête : Retour dans cercle blanc, nom correspondant, badge vert « Vérifié », menu « ⋮ » (MenuConversation)
 * - Carte blanche de l'annonce rattachée (vignette + titre + loyer bleu cobalt)
 * - Bulles de discussion : reçues en blanc, envoyées en bleu cobalt avec texte blanc
 * - Alerte de sécurité jaune "Ne paie jamais avant d'avoir visité..."
 * - Champ d'envoi pilule avec bouton circulaire bleu cobalt et icône Send.
 */
export function ConversationScreen() {
  const router = useRouter();
  const marges = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { etat, role } = useSession();
  const moi = etat.statut === "connecte" ? etat.user.id : "";

  useConversationFocus(id);
  const conversation = useConversation(id);
  const messages = useMessages(id);
  const envoyer = useEnvoyerMessage(id);
  const reprendre = useReprendreEnvoi(id);
  const lire = useLireConversation(id);
  const fiche = useFiche(conversation.data?.listing.slug ?? undefined);
  const lignes = useLignes(id, moi, conversation.data?.other_read_seq ?? 0, messages.data);
  const [texte, setTexte] = useState("");
  const [menu, setMenu] = useState(false);

  const dernierSeq = messages.data?.dernierSeq ?? 0;
  const maLecture = conversation.data?.my_read_seq ?? 0;
  useEffect(() => {
    if (dernierSeq > maLecture) lire.mutate(dernierSeq);
  }, [dernierSeq, maLecture]);

  if (conversation.isError) {
    return <ErrorState erreur={conversation.error} onRetry={() => void conversation.refetch()} />;
  }

  if (!conversation.data || !messages.data) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, padding: sp[4], gap: sp[3], paddingTop: marges.top + sp[4] }}>
        <Skeleton hauteur={50} />
        <Skeleton hauteur={80} />
        <Skeleton hauteur={150} />
      </View>
    );
  }

  const annonce = conversation.data.listing;
  const autreNom = conversation.data.other?.name ?? "Correspondant";
  // L'interlocuteur n'expose pas « vérifié » : on reprend celui du gérant sur la fiche (côté locataire uniquement).
  const autreVerifie = role !== "gerant" && !!fiche.data?.gerant?.verified;
  const couvertureAnnonce = fiche.data?.media.find((m) => m.is_cover) ?? fiche.data?.media[0];
  const imageAnnonce = urlMedia(couvertureAnnonce ? (couvertureAnnonce.kind === "video" ? couvertureAnnonce.poster_url : (couvertureAnnonce.thumb_url ?? couvertureAnnonce.url)) : null);
  const ecritureImpossible =
    conversation.data.status === "read_only" ||
    (conversation.data.status === "blocked" && !conversation.data.blocked_by_me);
  const erreurEnvoi =
    envoyer.error && isApiError(envoyer.error)
      ? messageErreur(envoyer.error.code, envoyer.error.message)
      : undefined;

  const handleEnvoi = () => {
    if (!texte.trim()) return;
    const msg = texte;
    setTexte("");
    envoyer.mutate(msg);
  };

  return (
    // Le champ de saisie remonte avec le clavier (iOS et Android « bord à bord ») : on voit ce qu'on écrit.
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === "ios" ? "padding" : "height"}>
      {/* Barre supérieure : collée sous la barre d'état, sans en-tête natif au-dessus */}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: 14,
          paddingHorizontal: sp[4],
          paddingTop: marges.top + sp[2],
          paddingBottom: sp[3],
          backgroundColor: "#FFFFFF",
          borderBottomWidth: 1,
          borderBottomColor: "rgba(15, 27, 61, 0.06)",
        }}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Retour"
          onPress={() => router.back()}
          style={{
            width: 40,
            height: 40,
            borderRadius: 20,
            backgroundColor: "#F1F5F9",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <ArrowLeft size={20} color={colors.night} />
        </Pressable>

        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <Text style={{ fontSize: 18, fontWeight: "800", color: colors.night }}>
            {autreNom}
          </Text>
          {autreVerifie ? (
            <View
              style={{
                backgroundColor: "#0D9488",
                paddingHorizontal: 8,
                paddingVertical: 3,
                borderRadius: rayon.pilule,
              }}
            >
              <View style={{ flexDirection: "row", alignItems: "center", gap: 3 }}>
                <BadgeCheck size={12} color="#FFFFFF" />
                <Text style={{ color: "#FFFFFF", fontSize: 11, fontWeight: "700" }}>Vérifié</Text>
              </View>
            </View>
          ) : null}
          {conversation.data.muted ? <BellOff size={16} color={colors.textMuted} accessibilityLabel="En sourdine" /> : null}
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Options de la conversation"
          onPress={() => setMenu(true)}
          hitSlop={8}
          style={{ marginLeft: "auto", width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center" }}
        >
          <EllipsisVertical size={22} color={colors.night} />
        </Pressable>
        <MenuConversation conversation={conversation.data} autreNom={autreNom} ouvert={menu} onFermer={() => setMenu(false)} />
      </View>

      {/* Carte d'annonce rattachée */}
      {annonce ? (
        <Pressable
          onPress={() => router.push(`/annonces/${annonce.slug}` as any)}
          style={{
            marginHorizontal: sp[4],
            marginTop: sp[3],
            marginBottom: sp[1],
            backgroundColor: "#FFFFFF",
            borderRadius: 18,
            padding: 12,
            flexDirection: "row",
            alignItems: "center",
            gap: 14,
            shadowColor: colors.night,
            shadowOffset: { width: 0, height: 2 },
            shadowOpacity: 0.05,
            shadowRadius: 8,
            elevation: 1,
          }}
        >
          <View
            style={{
              width: 50,
              height: 50,
              borderRadius: 12,
              backgroundColor: "#1E3A8A",
              overflow: "hidden",
            }}
          >
            {imageAnnonce ? (
              <Image source={{ uri: imageAnnonce }} style={{ width: "100%", height: "100%" }} />
            ) : null}
          </View>

          <View style={{ flex: 1, gap: 2 }}>
            <Text style={{ fontSize: 15, fontWeight: "700", color: colors.night }} numberOfLines={1}>
              {annonce.title}
            </Text>
            {fiche.data ? (
              <Text style={{ fontSize: 14, fontWeight: "800", color: colors.primary }}>
                {francs(fiche.data.rent_amount)}/mois
              </Text>
            ) : null}
          </View>
        </Pressable>
      ) : null}

      {/* Fil de discussion */}
      <FlatList
        inverted
        data={[...lignes].reverse()}
        keyExtractor={(l) => (l.type === "serveur" ? l.message.id : l.clientMsgId)}
        contentContainerStyle={{ padding: sp[4], gap: 14 }}
        onEndReached={() => void messages.chargerPlusAnciens()}
        ListFooterComponent={
          /* Avertissement de sécurité jaune en tête de discussion */
          <View
            style={{
              backgroundColor: "#FEF3C7",
              borderRadius: 16,
              padding: 14,
              marginBottom: sp[2],
            }}
          >
            <Text style={{ fontSize: 13, color: "#92400E", lineHeight: 18, fontWeight: "500" }}>
              Ne paie jamais avant d’avoir visité. Signale tout message suspect.
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const miens = item.type === "local" || item.message.sender_id === moi;
          const corps = item.type === "serveur" ? item.message.body : item.body;
          const heureTexte = item.type === "serveur" ? heure(item.message.created_at) : "…";

          return (
            <View style={{ alignSelf: miens ? "flex-end" : "flex-start", maxWidth: "80%" }}>
              <View
                style={{
                  backgroundColor: miens ? colors.primary : "#FFFFFF",
                  borderRadius: 18,
                  borderBottomRightRadius: miens ? 4 : 18,
                  borderBottomLeftRadius: miens ? 18 : 4,
                  paddingHorizontal: 16,
                  paddingVertical: 12,
                  shadowColor: colors.night,
                  shadowOffset: { width: 0, height: 1 },
                  shadowOpacity: 0.04,
                  shadowRadius: 4,
                  elevation: 1,
                }}
              >
                <Text
                  style={{
                    fontSize: 15,
                    lineHeight: 21,
                    color: miens ? "#FFFFFF" : colors.night,
                  }}
                >
                  {corps}
                </Text>
              </View>

              <Text
                style={{
                  fontSize: 11,
                  color: colors.textMuted,
                  marginTop: 4,
                  alignSelf: miens ? "flex-end" : "flex-start",
                }}
              >
                {heureTexte}
              </Text>

              {item.type === "local" && item.etat === "echec" ? (
                <View style={{ flexDirection: "row", gap: 8, marginTop: 4 }}>
                  <Pressable
                    onPress={() => void outbox.relancer(item.clientMsgId).then(reprendre)}
                  >
                    <Text style={{ fontSize: 12, color: colors.danger, fontWeight: "700" }}>
                      Renvoyer
                    </Text>
                  </Pressable>
                  <Pressable onPress={() => void outbox.retirer(item.clientMsgId)}>
                    <Text style={{ fontSize: 12, color: colors.textMuted }}>Supprimer</Text>
                  </Pressable>
                </View>
              ) : null}
            </View>
          );
        }}
      />

      {conversation.data.status === "blocked" && conversation.data.blocked_by_me ? (
        <View style={{ paddingHorizontal: sp[4], paddingVertical: sp[2], backgroundColor: colors.warningBg }}>
          <Text variante="legende" couleur={colors.warningText} style={{ textAlign: "center" }}>
            Tu as bloqué cette conversation : {autreNom} ne peut plus t’écrire. Pour débloquer, ouvre le menu ⋮.
          </Text>
        </View>
      ) : null}

      {/* Barre de saisie inférieure */}
      {ecritureImpossible ? (
        <View style={{ padding: sp[4], backgroundColor: "#FFFFFF" }}>
          <Text style={{ textAlign: "center", color: colors.textMuted, fontSize: 14 }}>
            {conversation.data.status === "read_only"
              ? "Cette conversation est en lecture seule."
              : `${autreNom} a bloqué cette conversation.`}
          </Text>
        </View>
      ) : (
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            paddingHorizontal: sp[4],
            paddingTop: 12,
            paddingBottom: Math.max(marges.bottom, 12),
            backgroundColor: "#FFFFFF",
            borderTopWidth: 1,
            borderTopColor: "rgba(15, 27, 61, 0.06)",
            gap: 12,
          }}
        >
          <View
            style={{
              flex: 1,
              backgroundColor: "#F8FAFC",
              borderRadius: 24,
              borderWidth: 1,
              borderColor: "rgba(15, 27, 61, 0.1)",
              paddingHorizontal: 16,
              minHeight: 46,
              justifyContent: "center",
            }}
          >
            <TextInput
              value={texte}
              onChangeText={setTexte}
              placeholder="Écris un message..."
              placeholderTextColor={colors.textMuted}
              multiline
              maxLength={2000}
              style={{
                fontSize: 15,
                color: colors.night,
                maxHeight: 100,
                paddingVertical: 8,
              }}
            />
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Envoyer le message"
            disabled={!texte.trim() || envoyer.isPending}
            onPress={handleEnvoi}
            style={{
              width: 46,
              height: 46,
              borderRadius: 23,
              backgroundColor: colors.primary,
              justifyContent: "center",
              alignItems: "center",
              opacity: !texte.trim() ? 0.6 : 1,
            }}
          >
            <Send size={18} color="#FFFFFF" style={{ marginLeft: 2 }} />
          </Pressable>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}
