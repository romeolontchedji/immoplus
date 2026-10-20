import { Linking, ScrollView, View } from "react-native";
import { useRouter } from "expo-router";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { Button } from "@/ui/components/Button";

type Section = { titre: string; contenu: string };

const SECTIONS: Section[] = [
  {
    titre: "Comment fonctionne Immo+ ?",
    contenu:
      "Immo+ met en relation les étudiants de Parakou avec des gérants de chambres vérifiés. Toutes les annonces sont accompagnées d'une vidéo réelle tournée sur place, garantissant la conformité de la chambre.",
  },
  {
    titre: "Comment contacter un gérant ?",
    contenu:
      "Depuis la fiche d'une annonce, appuie sur « Contacter le gérant ». La messagerie intégrée est le seul canal autorisé. Le numéro de téléphone du gérant n'est jamais communiqué pour protéger les deux parties.",
  },
  {
    titre: "Mes données sont-elles protégées ?",
    contenu:
      "Ton numéro de téléphone est utilisé uniquement pour la connexion et les notifications. Il n'est jamais transmis aux gérants ni aux autres utilisateurs.",
  },
  {
    titre: "Comment signaler un problème ?",
    contenu:
      "Depuis la fiche d'une annonce, utilise le bouton « Signaler » en bas de page. Notre équipe de modération traitera ton signalement dans les 24 heures.",
  },
  {
    titre: "Que faire si une chambre est déjà louée ?",
    contenu:
      "Appuie sur « Déjà louée ? » depuis la fiche de l'annonce. Le gérant sera notifié pour mettre l'annonce à jour.",
  },
];

/** Aide et conditions d'utilisation (statique). */
export function AideScreen() {
  const { c } = useTheme();
  const router = useRouter();

  return (
    <Screen scroll>
      <Text variante="titre">Aide</Text>

      {/* FAQ */}
      <View style={{ gap: sp[4] }}>
        {SECTIONS.map((s) => (
          <View
            key={s.titre}
            style={{
              padding: sp[4],
              borderRadius: 16,
              borderWidth: 1,
              borderColor: c.border,
              backgroundColor: c.surface,
              gap: sp[2],
            }}
          >
            <Text variante="corpsGras">{s.titre}</Text>
            <Text muted>{s.contenu}</Text>
          </View>
        ))}
      </View>

      {/* Liens légaux */}
      <View style={{ gap: sp[3], paddingTop: sp[2] }}>
        <Text variante="label">Documents légaux</Text>
        <Button
          titre="Conditions d'utilisation"
          variante="secondaire"
          onPress={() => router.push("/legal/conditions")}
        />
        <Button
          titre="Politique de confidentialité"
          variante="fantome"
          onPress={() => router.push("/legal/confidentialite")}
        />
      </View>

      <Text variante="legende" muted style={{ textAlign: "center" }}>
        Immo+ · Version 1.0.0 · Parakou, Bénin
      </Text>
    </Screen>
  );
}
