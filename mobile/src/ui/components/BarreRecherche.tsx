import { forwardRef, useEffect, useRef, useState } from "react";
import { Pressable, TextInput, View } from "react-native";
import { Search, SlidersHorizontal, X } from "lucide-react-native";
import { colors, CIBLE_MIN, ombre, rayon, sp } from "@/ui/theme/tokens";
import { Text } from "./Text";

type Props = {
  /** Valeur appliquée (filtres partagés) : le champ se resynchronise quand elle change ailleurs. */
  valeur: string;
  /** Appelé après une courte pause de saisie, à la validation et à l'effacement. */
  onRecherche: (texte: string) => void;
  onFiltres: () => void;
  /** Nombre de filtres actifs, en pastille sur le bouton. */
  nbFiltres?: number;
  autoFocus?: boolean;
  placeholder?: string;
};

const PAUSE_MS = 200;

/**
 * Barre de recherche mobile (maquette Accueil) : loupe, saisie directe, bouton d'effacement, bouton « Filtres » cobalt
 * avec compteur. La recherche part toute seule après une pause de frappe : pas besoin de valider au clavier.
 */
export const BarreRecherche = forwardRef<TextInput, Props>(function BarreRecherche(
  { valeur, onRecherche, onFiltres, nbFiltres = 0, autoFocus, placeholder = "Quartier, repère, type…" },
  ref,
) {
  const [texte, setTexte] = useState(valeur);
  const [focus, setFocus] = useState(false);
  const minuteur = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const envoye = useRef(valeur);

  useEffect(() => {
    if (valeur !== envoye.current) {
      envoye.current = valeur;
      setTexte(valeur);
    }
  }, [valeur]);
  useEffect(() => () => clearTimeout(minuteur.current), []);

  const envoyer = (v: string) => {
    clearTimeout(minuteur.current);
    if (v.trim() === envoye.current.trim()) return;
    envoye.current = v;
    onRecherche(v);
  };

  const changer = (v: string) => {
    setTexte(v);
    clearTimeout(minuteur.current);
    minuteur.current = setTimeout(() => envoyer(v), PAUSE_MS);
  };

  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: sp[2],
        minHeight: 56,
        paddingLeft: sp[4],
        paddingRight: 6,
        backgroundColor: colors.surface,
        borderRadius: rayon.card,
        borderWidth: 1.5,
        borderColor: focus ? colors.primary : "transparent",
        ...ombre.card,
      }}
    >
      <Search size={20} color={focus ? colors.primary : colors.textMuted} />
      <TextInput
        ref={ref}
        value={texte}
        onChangeText={changer}
        onSubmitEditing={() => envoyer(texte)}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        autoFocus={autoFocus}
        placeholder={placeholder}
        placeholderTextColor={colors.textMuted}
        returnKeyType="search"
        autoCorrect={false}
        accessibilityLabel="Rechercher une chambre"
        style={{ flex: 1, minHeight: CIBLE_MIN, fontSize: 16, fontWeight: "500", color: colors.night, paddingVertical: 0 }}
      />
      {texte ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Effacer la recherche"
          hitSlop={8}
          onPress={() => {
            setTexte("");
            envoyer("");
          }}
          style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: colors.divider, alignItems: "center", justifyContent: "center" }}
        >
          <X size={16} color={colors.night} />
        </Pressable>
      ) : null}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={nbFiltres ? `Filtres, ${nbFiltres} actifs` : "Ouvrir les filtres"}
        onPress={onFiltres}
        style={({ pressed }) => ({
          flexDirection: "row",
          alignItems: "center",
          gap: 6,
          minHeight: 44,
          paddingHorizontal: 14,
          borderRadius: rayon.field,
          backgroundColor: pressed ? colors.blueHover : colors.primary,
        })}
      >
        <SlidersHorizontal size={16} color={colors.white} />
        <Text style={{ color: colors.white, fontSize: 14, fontWeight: "700" }}>Filtres</Text>
        {nbFiltres ? (
          <View style={{ minWidth: 20, height: 20, borderRadius: 10, paddingHorizontal: 5, backgroundColor: colors.sun, alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: colors.night, fontSize: 12, fontWeight: "800" }}>{nbFiltres}</Text>
          </View>
        ) : null}
      </Pressable>
    </View>
  );
});
