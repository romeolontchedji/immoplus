import { useState, type ReactNode } from "react";
import { FlatList, Modal, Pressable, TextInput, View } from "react-native";
import { Check, ChevronDown, Search } from "lucide-react-native";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { Button } from "./Button";
import { Text } from "./Text";

export type Option = { valeur: string; libelle: string; aide?: string };

type Props = {
  label: string;
  options: Option[];
  /** Valeurs choisies (une seule en mode simple). */
  valeurs: string[];
  onChange: (valeurs: string[]) => void;
  multiple?: boolean;
  placeholder?: string;
  /** Recherche affichée au-delà de 8 options. */
  recherche?: boolean;
  /** Contenu ajouté sous la liste (ex. « Autre montant »). */
  pied?: ReactNode;
};

/**
 * Liste déroulante (plan v2, P1.3) : un champ qui résume la sélection et ouvre une feuille basse avec recherche.
 * Simple : un appui choisit et ferme. Multiple : cases à cocher puis « Valider ».
 */
export function ListeDeroulante({ label, options, valeurs, onChange, multiple = false, placeholder = "Choisir", recherche, pied }: Props) {
  const [ouvert, setOuvert] = useState(false);
  const [brouillon, setBrouillon] = useState<string[]>(valeurs);
  const [texte, setTexte] = useState("");
  const avecRecherche = recherche ?? options.length > 8;
  const choisis = options.filter((o) => valeurs.includes(o.valeur)).map((o) => o.libelle);
  const resume = choisis.length === 0 ? placeholder : choisis.length <= 2 ? choisis.join(", ") : `${choisis.slice(0, 2).join(", ")} +${choisis.length - 2}`;
  const visibles = options.filter((o) => !texte.trim() || o.libelle.toLowerCase().includes(texte.trim().toLowerCase()));

  const ouvrir = () => {
    setBrouillon(valeurs);
    setTexte("");
    setOuvert(true);
  };
  const appuyer = (v: string) => {
    if (!multiple) {
      onChange(valeurs[0] === v ? [] : [v]);
      setOuvert(false);
      return;
    }
    setBrouillon((b) => (b.includes(v) ? b.filter((x) => x !== v) : [...b, v]));
  };

  return (
    <View style={{ gap: sp[2] }}>
      <Text variante="label" muted>{label}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${label} : ${resume}`}
        onPress={ouvrir}
        style={{ minHeight: 52, flexDirection: "row", alignItems: "center", gap: sp[2], borderWidth: 1.5, borderColor: choisis.length ? colors.primary : colors.border, borderRadius: rayon.field, backgroundColor: colors.surface, paddingHorizontal: sp[4] }}
      >
        <Text style={{ flex: 1, fontSize: 16, fontWeight: choisis.length ? "600" : "400", color: choisis.length ? colors.night : colors.textMuted }} numberOfLines={1}>{resume}</Text>
        <ChevronDown size={20} color={colors.textMuted} />
      </Pressable>

      <Modal transparent animationType="slide" visible={ouvert} onRequestClose={() => setOuvert(false)} statusBarTranslucent>
        <Pressable accessibilityLabel="Fermer" onPress={() => setOuvert(false)} style={{ flex: 1, backgroundColor: "rgba(15, 27, 61, 0.45)" }} />
        <View style={{ maxHeight: "80%", backgroundColor: colors.surface, borderTopLeftRadius: rayon.sheet, borderTopRightRadius: rayon.sheet, paddingTop: sp[3], paddingBottom: sp[8] }}>
          <View style={{ alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: colors.border }} />
          <Text variante="titreSection" style={{ paddingHorizontal: sp[5], paddingVertical: sp[3] }}>{label}</Text>
          {avecRecherche ? (
            <View style={{ marginHorizontal: sp[5], marginBottom: sp[2], flexDirection: "row", alignItems: "center", gap: sp[2], backgroundColor: colors.bg, borderRadius: rayon.pilule, paddingHorizontal: sp[4], height: 44 }}>
              <Search size={18} color={colors.textMuted} />
              <TextInput value={texte} onChangeText={setTexte} placeholder="Rechercher" placeholderTextColor={colors.textMuted} accessibilityLabel={`Rechercher dans ${label}`} style={{ flex: 1, fontSize: 15, color: colors.night, paddingVertical: 0 }} />
            </View>
          ) : null}
          <FlatList
            data={visibles}
            keyExtractor={(o) => o.valeur}
            keyboardShouldPersistTaps="handled"
            ListEmptyComponent={<Text muted style={{ textAlign: "center", padding: sp[6] }}>Aucun résultat.</Text>}
            renderItem={({ item }) => {
              const actif = (multiple ? brouillon : valeurs).includes(item.valeur);
              return (
                <Pressable
                  accessibilityRole={multiple ? "checkbox" : "radio"}
                  accessibilityState={{ checked: actif }}
                  onPress={() => appuyer(item.valeur)}
                  style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: sp[3], paddingHorizontal: sp[5], minHeight: 52, backgroundColor: pressed ? colors.bg : "transparent" })}
                >
                  <View style={{ flex: 1 }}>
                    <Text variante={actif ? "corpsGras" : "corps"}>{item.libelle}</Text>
                    {item.aide ? <Text variante="legende" muted>{item.aide}</Text> : null}
                  </View>
                  {actif ? <Check size={20} color={colors.primary} /> : null}
                </Pressable>
              );
            }}
          />
          {pied ? <View style={{ paddingHorizontal: sp[5], paddingTop: sp[2] }}>{pied}</View> : null}
          {multiple ? (
            <View style={{ flexDirection: "row", gap: sp[3], paddingHorizontal: sp[5], paddingTop: sp[3] }}>
              <View style={{ flex: 1 }}><Button titre="Tout effacer" variante="fantome" onPress={() => setBrouillon([])} /></View>
              <View style={{ flex: 1 }}><Button titre={brouillon.length ? `Valider (${brouillon.length})` : "Valider"} onPress={() => { onChange(brouillon); setOuvert(false); }} /></View>
            </View>
          ) : null}
        </View>
      </Modal>
    </View>
  );
}
