import { useRef, type ReactNode } from "react";
import { Pressable, View } from "react-native";
import { Swipeable } from "react-native-gesture-handler";
import { Bell, BellOff, CheckCheck } from "lucide-react-native";
import { colors, sp } from "@/ui/theme/tokens";
import { Text } from "@/ui/components/Text";
import { useLireConversation, useSourdine } from "./queries";

const HUIT_HEURES = 8 * 3_600_000;
const TOUT = 2_147_483_647; // le serveur borne au dernier message

/** Bouton révélé par le balayage vers la gauche. */
function Action({ libelle, icone: Icone, fond, onPress }: { libelle: string; icone: typeof Bell; fond: string; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={libelle} onPress={onPress} style={{ width: 84, backgroundColor: fond, justifyContent: "center", alignItems: "center", gap: sp[1] }}>
      <Icone size={20} color={colors.white} />
      <Text variante="legende" couleur={colors.white} style={{ fontWeight: "700" }}>{libelle}</Text>
    </Pressable>
  );
}

/**
 * Balayage d'une ligne de conversation (plan v2, MM2) : « Lu » quand il reste des non-lus, sourdine 8 h ou
 * réactivation. Les autres choix (durées, blocage, signalement) restent dans l'appui long.
 */
export function BalayageConversation({ conversation, children }: { conversation: { id: string; muted: boolean; unread_count: number }; children: ReactNode }) {
  const ref = useRef<Swipeable>(null);
  const lire = useLireConversation(conversation.id);
  const sourdine = useSourdine(conversation.id);
  const puis = (f: () => void) => () => {
    ref.current?.close();
    f();
  };
  return (
    <Swipeable
      ref={ref}
      friction={2}
      rightThreshold={40}
      overshootRight={false}
      renderRightActions={() => (
        <View style={{ flexDirection: "row" }}>
          {conversation.unread_count > 0 ? <Action libelle="Lu" icone={CheckCheck} fond={colors.primary} onPress={puis(() => lire.mutate(TOUT))} /> : null}
          {conversation.muted ? (
            <Action libelle="Réactiver" icone={Bell} fond={colors.night} onPress={puis(() => sourdine.mutate(null))} />
          ) : (
            <Action libelle="Sourdine" icone={BellOff} fond={colors.textMuted} onPress={puis(() => sourdine.mutate(new Date(Date.now() + HUIT_HEURES)))} />
          )}
        </View>
      )}
    >
      {children}
    </Swipeable>
  );
}
