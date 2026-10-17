import { useState } from "react";
import { View } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { Eye, Heart, MessageCircle, type LucideIcon } from "lucide-react-native";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Chip } from "@/ui/components/Chip";
import { Pastille } from "@/ui/components/Groupe";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useAnnoncePro, useStatistiques } from "./queries";

function Tuile({ icone, teinte, valeur, libelle }: { icone: LucideIcon; teinte: "bleu" | "rouge" | "vert"; valeur: number; libelle: string }) {
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface, borderRadius: rayon.card, padding: sp[3], gap: sp[2], borderWidth: 1, borderColor: colors.divider, ...ombre.card }}>
      <Pastille icone={icone} teinte={teinte} taille={32} />
      <Text style={{ fontSize: 26, fontWeight: "800", color: colors.night }}>{valeur}</Text>
      <Text variante="legende" muted>{libelle}</Text>
    </View>
  );
}

/** Barres des vues jour par jour : hauteur relative au maximum de la période, contacts en pastille soleil. */
function Graphique({ jours }: { jours: { day: string; views: number; contacts: number }[] }) {
  const max = Math.max(1, ...jours.map((j) => j.views));
  const court = jours.length <= 7;
  return (
    <View style={{ backgroundColor: colors.surface, borderRadius: rayon.card, padding: sp[4], gap: sp[3], borderWidth: 1, borderColor: colors.divider }}>
      <Text variante="corpsGras">Vues par jour</Text>
      <View style={{ height: 140, flexDirection: "row", alignItems: "flex-end", gap: court ? sp[2] : 2 }} accessibilityLabel={`Vues par jour, maximum ${max}`}>
        {jours.map((j) => (
          <View key={j.day} style={{ flex: 1, alignItems: "center", justifyContent: "flex-end", height: "100%", gap: 4 }}>
            {j.contacts ? <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: colors.sun }} /> : null}
            <View style={{ width: "100%", height: `${Math.max(2, (j.views / max) * 100)}%`, backgroundColor: j.views ? colors.blue : colors.divider, borderRadius: 4 }} />
          </View>
        ))}
      </View>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <Text variante="legende" muted>{new Date(jours[0]?.day ?? "").toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}</Text>
        <Text variante="legende" muted>Aujourd’hui</Text>
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: colors.sun }} />
        <Text variante="legende" muted>Jour avec au moins un contact</Text>
      </View>
    </View>
  );
}

/** Statistiques d'une annonce (EF-DSH-04 ; plan v2, MM7) : même source que le tableau de bord et le site. */
export function AnnonceStatsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [jours, setJours] = useState<7 | 30>(30);
  const annonce = useAnnoncePro(id);
  const requete = useStatistiques(id, jours);

  return (
    <Screen scroll>
      <View style={{ gap: sp[1] }}>
        <Text variante="titre">Statistiques</Text>
        {annonce.data ? <Text muted numberOfLines={1}>{annonce.data.title}</Text> : null}
      </View>
      <View style={{ flexDirection: "row", gap: sp[2] }}>
        <Chip titre="7 jours" actif={jours === 7} onPress={() => setJours(7)} />
        <Chip titre="30 jours" actif={jours === 30} onPress={() => setJours(30)} />
      </View>
      <QueryState query={requete}>
        {(s) => (
          <>
            <View style={{ flexDirection: "row", gap: sp[3] }}>
              <Tuile icone={Eye} teinte="bleu" valeur={s.views} libelle="Vues" />
              <Tuile icone={Heart} teinte="rouge" valeur={s.favorites} libelle="Favoris" />
              <Tuile icone={MessageCircle} teinte="vert" valeur={s.contacts} libelle="Contacts" />
            </View>
            <Graphique jours={s.daily} />
            <Text variante="legende" muted>
              Une vue est comptée une fois par personne et par jour. Les chiffres du jour s’actualisent toutes les 5 minutes.
            </Text>
          </>
        )}
      </QueryState>
    </Screen>
  );
}
