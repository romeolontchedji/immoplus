import { Alert, Modal, Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { Ban, Bell, BellOff, Flag, Home, ShieldCheck } from "lucide-react-native";
import { t } from "@/i18n/fr";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { GroupeListe, LigneListe } from "@/ui/components/Groupe";
import { Text } from "@/ui/components/Text";
import { useBloquer, useSourdine } from "./queries";

type Conversation = { id: string; status: string; blocked_by_me: boolean; muted: boolean; listing: { slug: string | null } };

const HEURE = 3_600_000;
const plus = (ms: number) => new Date(Date.now() + ms);

/**
 * Menu « ⋮ » d'une conversation (plan v2, MM3) : sourdine 8 h / 1 semaine / toujours, bloquer ou débloquer (avec
 * confirmation), signaler, voir la chambre. Feuille basse, actions effectives côté serveur.
 */
export function MenuConversation({ conversation, autreNom, ouvert, onFermer }: { conversation: Conversation; autreNom: string; ouvert: boolean; onFermer: () => void }) {
  const router = useRouter();
  const sourdine = useSourdine(conversation.id);
  const bloque = conversation.status === "blocked";
  const bloquer = useBloquer(conversation.id, !bloque);
  const faire = (f: () => void) => () => {
    onFermer();
    f();
  };

  const confirmerBlocage = () =>
    Alert.alert(
      bloque ? `Débloquer ${autreNom} ?` : `Bloquer ${autreNom} ?`,
      bloque ? "Vous pourrez de nouveau vous écrire." : "Vous ne pourrez plus vous écrire. Tu pourras débloquer à tout moment.",
      [{ text: t.commun.annuler, style: "cancel" }, { text: bloque ? "Débloquer" : "Bloquer", style: bloque ? "default" : "destructive", onPress: () => bloquer.mutate() }],
    );

  return (
    <Modal transparent animationType="slide" visible={ouvert} onRequestClose={onFermer} statusBarTranslucent>
      <Pressable accessibilityLabel="Fermer" onPress={onFermer} style={{ flex: 1, backgroundColor: "rgba(15, 27, 61, 0.45)" }} />
      <View style={{ backgroundColor: colors.bg, borderTopLeftRadius: rayon.sheet, borderTopRightRadius: rayon.sheet, padding: sp[4], paddingBottom: sp[10], gap: sp[4] }}>
        <View style={{ alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: colors.border }} />
        <Text variante="titreSection" style={{ textAlign: "center" }}>{autreNom}</Text>
        {conversation.muted ? (
          <GroupeListe>
            <LigneListe titre="Réactiver les notifications" icone={Bell} onPress={faire(() => sourdine.mutate(null))} />
          </GroupeListe>
        ) : (
          <GroupeListe titre="Mettre en sourdine">
            <LigneListe titre="Pendant 8 heures" icone={BellOff} teinte="gris" onPress={faire(() => sourdine.mutate(plus(8 * HEURE)))} />
            <LigneListe titre="Pendant 1 semaine" icone={BellOff} teinte="gris" onPress={faire(() => sourdine.mutate(plus(7 * 24 * HEURE)))} />
            <LigneListe titre="Toujours" icone={BellOff} teinte="gris" onPress={faire(() => sourdine.mutate(plus(10 * 365 * 24 * HEURE)))} />
          </GroupeListe>
        )}
        <GroupeListe>
          {conversation.listing.slug ? (
            <LigneListe titre="Voir la chambre" icone={Home} onPress={faire(() => router.push({ pathname: "/annonces/[ident]", params: { ident: conversation.listing.slug as string } }))} />
          ) : null}
          <LigneListe titre="Signaler la conversation" icone={Flag} teinte="soleil" onPress={faire(() => router.push(`/signaler?type=conversation&id=${conversation.id}` as never))} />
          {!bloque || conversation.blocked_by_me ? (
            <LigneListe titre={bloque ? "Débloquer" : "Bloquer"} icone={bloque ? ShieldCheck : Ban} danger={!bloque} onPress={faire(confirmerBlocage)} droite={null} />
          ) : null}
        </GroupeListe>
      </View>
    </Modal>
  );
}
