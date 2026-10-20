import type { ReactNode } from "react";
import { Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { ArrowLeft, Bell } from "lucide-react-native";
import { colors, ombre, sp } from "@/ui/theme/tokens";
import { Logotype } from "./Logo";
import { Text } from "./Text";

type Props = {
  titre: string;
  sousTitre?: string;
  /** Sous-page : bouton retour à la place du logo. */
  retour?: boolean;
  /** Action à droite (bouton « Publier »…). Par défaut sur un onglet : la cloche des notifications. */
  droite?: ReactNode;
  /** Contenu placé sous le titre (recherche, filtres…). */
  children?: ReactNode;
};

function BoutonRond({ libelle, onPress, children }: { libelle: string; onPress: () => void; children: ReactNode }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={libelle}
      onPress={onPress}
      hitSlop={6}
      style={({ pressed }) => ({ width: 44, height: 44, borderRadius: 14, backgroundColor: pressed ? colors.divider : colors.surface, alignItems: "center", justifyContent: "center", ...ombre.card })}
    >
      {children}
    </Pressable>
  );
}

/**
 * Haut de page commun à tous les écrans : une rangée (logo ou retour à gauche, action à droite), puis le titre et
 * son sous-titre, aux mêmes tailles et marges partout. Disposition de l'accueil, reprise sur chaque onglet.
 */
export function EnTetePage({ titre, sousTitre, retour, droite, children }: Props) {
  const router = useRouter();
  const action =
    droite === undefined && !retour ? (
      <BoutonRond libelle="Notifications" onPress={() => router.push("/notifications")}>
        <Bell size={20} color={colors.night} />
      </BoutonRond>
    ) : (
      droite
    );
  return (
    <View style={{ gap: sp[3], paddingTop: sp[2], paddingBottom: sp[1] }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", minHeight: 44 }}>
        {retour ? (
          <BoutonRond libelle="Retour" onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))}>
            <ArrowLeft size={20} color={colors.night} />
          </BoutonRond>
        ) : (
          <Logotype taille={26} />
        )}
        {action ?? null}
      </View>
      <View style={{ gap: sp[1] }}>
        <Text accessibilityRole="header" style={{ fontSize: 28, lineHeight: 34, fontWeight: "800", color: colors.night, letterSpacing: -0.5 }}>
          {titre}
        </Text>
        {sousTitre ? <Text muted style={{ fontSize: 15, lineHeight: 22 }}>{sousTitre}</Text> : null}
      </View>
      {children}
    </View>
  );
}
