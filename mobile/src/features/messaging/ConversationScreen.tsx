import { useEffect, useState } from "react";
import { FlatList, Pressable, TextInput, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { ArrowLeft, Send } from "lucide-react-native";
import { Image } from "expo-image";
import { isApiError } from "@/api/errors";
import { fcfa, heure } from "@/lib/format";
import { messageErreur } from "@/i18n/fr";
import { useConversationFocus } from "@/realtime/RealtimeProvider";
import { useSession } from "@/state/session";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { outbox } from "@/storage/outbox";
import { ErrorState } from "@/ui/components/States";
import { Skeleton } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
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
 * - En-tête : Retour dans cercle blanc, nom correspondant, badge vert "✓ Vérifié"
 * - Carte blanche de l'annonce rattachée (vignette + titre + loyer bleu cobalt)
 * - Bulles de discussion : reçues en blanc, envoyées en bleu cobalt avec texte blanc
 * - Alerte de sécurité jaune "Ne paie jamais avant d'avoir visité..."
 * - Champ d'envoi pilule avec bouton circulaire bleu cobalt et icône Send.
 */
export function ConversationScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { etat } = useSession();
  const moi = etat.statut === "connecte" ? etat.user.id : "";

  useConversationFocus(id);
  const conversation = useConversation(id);
  const messages = useMessages(id);
  const envoyer = useEnvoyerMessage(id);
  const reprendre = useReprendreEnvoi(id);
  const lire = useLireConversation(id);
  const lignes = useLignes(id, moi, conversation.data?.other_read_seq ?? 0, messages.data);
  const [texte, setTexte] = useState("");

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
      <View style={{ flex: 1, backgroundColor: colors.bg, padding: sp[4], gap: sp[3], paddingTop: 60 }}>
        <Skeleton hauteur={50} />
        <Skeleton hauteur={80} />
        <Skeleton hauteur={150} />
      </View>
    );
  }

  const annonce = conversation.data.listing;
  const autreNom = conversation.data.other_party?.name ?? "Correspondant";
  const autreVerifie = conversation.data.other_party?.verified ?? true;
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
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      {/* Barre supérieure */}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: 14,
          paddingHorizontal: sp[4],
          paddingTop: 54,
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
              <Text style={{ color: "#FFFFFF", fontSize: 11, fontWeight: "700" }}>✓ Vérifié</Text>
            </View>
          ) : null}
        </View>
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
            {annonce.cover_url ? (
              <Image source={{ uri: annonce.cover_url }} style={{ width: "100%", height: "100%" }} />
            ) : null}
          </View>

          <View style={{ flex: 1, gap: 2 }}>
            <Text style={{ fontSize: 15, fontWeight: "700", color: colors.night }} numberOfLines={1}>
              {annonce.title}
            </Text>
            <Text style={{ fontSize: 14, fontWeight: "800", color: colors.primary }}>
              {fcfa(annonce.rent_amount)}/mois
            </Text>
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

      {/* Barre de saisie inférieure */}
      {ecritureImpossible ? (
        <View style={{ padding: sp[4], backgroundColor: "#FFFFFF" }}>
          <Text style={{ textAlign: "center", color: colors.textMuted, fontSize: 14 }}>
            {conversation.data.status === "read_only"
              ? "Cette conversation est en lecture seule."
              : "Cette conversation est bloquée."}
          </Text>
        </View>
      ) : (
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            paddingHorizontal: sp[4],
            paddingVertical: 12,
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
    </View>
  );
}
