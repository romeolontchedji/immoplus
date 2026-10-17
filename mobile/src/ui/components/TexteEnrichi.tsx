import { View } from "react-native";
import { analyserMarkdown, type Segment } from "@/lib/miseEnForme";
import { colors, sp } from "@/ui/theme/tokens";
import { Text } from "./Text";

const CORPS = { fontSize: 15, lineHeight: 23, color: colors.night } as const;

function Segments({ liste }: { liste: Segment[] }) {
  return (
    <>
      {liste.map((s, i) => (
        <Text key={i} style={[CORPS, s.gras ? { fontWeight: "700" } : null, s.italique ? { fontStyle: "italic" } : null]}>
          {s.texte}
        </Text>
      ))}
    </>
  );
}

/** Description d'annonce en Markdown restreint (gras, italique, intertitres, listes), sans afficher les `**`. */
export function TexteEnrichi({ md }: { md: string }) {
  return (
    <View style={{ gap: sp[3] }}>
      {analyserMarkdown(md).map((bloc, i) => {
        if (bloc.type === "titre") {
          return <Text key={i} variante="corpsGras" style={{ fontSize: 17, marginTop: i ? sp[1] : 0 }}><Segments liste={bloc.segments} /></Text>;
        }
        if (bloc.type === "paragraphe") return <Text key={i} style={CORPS}><Segments liste={bloc.segments} /></Text>;
        return (
          <View key={i} style={{ gap: sp[1] }}>
            {bloc.elements.map((element, j) => (
              <View key={j} style={{ flexDirection: "row", gap: sp[2], paddingLeft: sp[1] }}>
                <Text style={[CORPS, { minWidth: 18, color: colors.textMuted }]}>{bloc.ordonnee ? `${j + 1}.` : "•"}</Text>
                <Text style={[CORPS, { flex: 1 }]}><Segments liste={element} /></Text>
              </View>
            ))}
          </View>
        );
      })}
    </View>
  );
}
