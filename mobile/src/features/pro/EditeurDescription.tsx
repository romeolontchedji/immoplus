import { useState } from "react";
import { Pressable, TextInput, View } from "react-native";
import { Bold, Eye, Heading, Italic, List, ListOrdered, PenLine, type LucideIcon } from "lucide-react-native";
import { appliquerFormat, type Format } from "@/lib/miseEnForme";
import { TexteEnrichi } from "@/ui/components/TexteEnrichi";
import { Text } from "@/ui/components/Text";
import { colors, fs, rayon, sp } from "@/ui/theme/tokens";

const OUTILS: { format: Format; icone: LucideIcon; nom: string }[] = [
  { format: "gras", icone: Bold, nom: "Gras" },
  { format: "italique", icone: Italic, nom: "Italique" },
  { format: "titre", icone: Heading, nom: "Intertitre" },
  { format: "liste", icone: List, nom: "Liste à puces" },
  { format: "liste-numerotee", icone: ListOrdered, nom: "Liste numérotée" },
];

function Outil({ nom, icone: Icone, actif, desactive, onPress }: { nom: string; icone: LucideIcon; actif?: boolean; desactive?: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={nom}
      accessibilityState={{ disabled: desactive, selected: actif }}
      disabled={desactive}
      onPress={onPress}
      hitSlop={4}
      style={({ pressed }) => ({
        width: 40, height: 40, borderRadius: 12, alignItems: "center", justifyContent: "center",
        backgroundColor: actif ? colors.primary : pressed ? colors.blueSoft : "transparent",
        opacity: desactive ? 0.35 : 1,
      })}
    >
      <Icone size={19} color={actif ? colors.white : colors.night} />
    </Pressable>
  );
}

/**
 * Description enrichie (décision V6) : barre gras, italique, intertitre, listes au-dessus du champ, et aperçu rendu
 * comme sur la fiche. Le Markdown produit est celui qu'accepte le serveur (qui reste seul juge à l'enregistrement).
 */
export function EditeurDescription({ valeur, onChange, placeholder }: { valeur: string; onChange: (v: string) => void; placeholder?: string }) {
  const [selection, setSelection] = useState({ start: valeur.length, end: valeur.length });
  const [apercu, setApercu] = useState(false);

  const appliquer = (format: Format) => {
    const r = appliquerFormat(format, valeur, selection.start, selection.end);
    onChange(r.texte);
    setSelection({ start: r.debut, end: r.fin });
  };

  return (
    <View style={{ gap: sp[2] }}>
      <Text variante="label">Description</Text>
      <View style={{ borderWidth: 1.5, borderColor: colors.border, borderRadius: rayon.card, overflow: "hidden", backgroundColor: colors.surface }}>
        <View
          accessibilityRole="toolbar"
          style={{ flexDirection: "row", alignItems: "center", gap: 2, padding: sp[1], backgroundColor: colors.bg, borderBottomWidth: 1, borderBottomColor: colors.border }}
        >
          {OUTILS.map((o) => <Outil key={o.format} nom={o.nom} icone={o.icone} desactive={apercu} onPress={() => appliquer(o.format)} />)}
          <View style={{ flex: 1 }} />
          <Outil nom={apercu ? "Revenir à l'écriture" : "Aperçu"} icone={apercu ? PenLine : Eye} actif={apercu} onPress={() => setApercu(!apercu)} />
        </View>
        {apercu ? (
          <View style={{ minHeight: 160, padding: sp[4] }}>
            {valeur.trim() ? <TexteEnrichi md={valeur} /> : <Text muted>Rien à afficher pour l’instant.</Text>}
          </View>
        ) : (
          <TextInput
            accessibilityLabel="Description"
            multiline
            value={valeur}
            onChangeText={onChange}
            selection={selection}
            onSelectionChange={(e) => setSelection(e.nativeEvent.selection)}
            placeholder={placeholder}
            placeholderTextColor={colors.textMuted}
            textAlignVertical="top"
            style={{ minHeight: 160, padding: sp[4], fontSize: fs[16], lineHeight: 23, color: colors.night }}
          />
        )}
      </View>
      <Text variante="legende" muted>Sélectionne un mot puis choisis un style. Les liens et les numéros de téléphone sont retirés.</Text>
    </View>
  );
}
