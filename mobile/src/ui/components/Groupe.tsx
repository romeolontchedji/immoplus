import { Children, Fragment, isValidElement, type ReactNode } from "react";
import { Pressable, View } from "react-native";
import { ChevronRight, type LucideIcon } from "lucide-react-native";
import { CIBLE_MIN, colors, ombre, rayon, sp } from "@/ui/theme/tokens";
import { FondMotif } from "./FondMotif";
import { Text } from "./Text";

type Teinte = "bleu" | "soleil" | "vert" | "rouge" | "gris";
const TEINTES: Record<Teinte, { fond: string; trait: string }> = {
  bleu: { fond: colors.blueSoft, trait: colors.blue },
  soleil: { fond: colors.warningBg, trait: colors.warning },
  vert: { fond: colors.successBg, trait: colors.success },
  rouge: { fond: colors.dangerBg, trait: colors.danger },
  gris: { fond: colors.divider, trait: colors.textMuted },
};

/** Icône dans une pastille teintée (captures « épurées »). */
export function Pastille({ icone: Icone, teinte = "bleu", taille = 40 }: { icone: LucideIcon; teinte?: Teinte; taille?: number }) {
  const t = TEINTES[teinte];
  return (
    <View style={{ width: taille, height: taille, borderRadius: taille * 0.32, backgroundColor: t.fond, alignItems: "center", justifyContent: "center" }}>
      <Icone size={taille * 0.5} color={t.trait} />
    </View>
  );
}

/** Liste groupée en carte (façon Réglages) : titre de section, lignes séparées par un filet. */
export function GroupeListe({ titre, children }: { titre?: string; children: ReactNode }) {
  const lignes = Children.toArray(children).filter(isValidElement);
  return (
    <View style={{ gap: sp[2] }}>
      {titre ? <Text variante="label" muted style={{ paddingHorizontal: sp[1] }}>{titre}</Text> : null}
      <View style={{ backgroundColor: colors.surface, borderRadius: rayon.card, borderWidth: 1, borderColor: colors.divider, overflow: "hidden", ...ombre.card }}>
        {lignes.map((ligne, i) => (
          <Fragment key={i}>
            {i > 0 ? <View style={{ height: 1, backgroundColor: colors.divider, marginLeft: 68 }} /> : null}
            {ligne}
          </Fragment>
        ))}
      </View>
    </View>
  );
}

type LigneProps = {
  titre: string;
  sousTitre?: string;
  icone?: LucideIcon;
  teinte?: Teinte;
  onPress?: () => void;
  /** Élément à droite (interrupteur, pastille) ; par défaut un chevron si la ligne est pressable. */
  droite?: ReactNode;
  danger?: boolean;
};

export function LigneListe({ titre, sousTitre, icone, teinte = "bleu", onPress, droite, danger }: LigneProps) {
  const contenu = (pressed: boolean) => (
    <View style={{ minHeight: CIBLE_MIN + 12, flexDirection: "row", alignItems: "center", gap: sp[3], paddingHorizontal: sp[4], paddingVertical: sp[3], backgroundColor: pressed ? colors.bg : "transparent" }}>
      {icone ? <Pastille icone={icone} teinte={danger ? "rouge" : teinte} /> : null}
      <View style={{ flex: 1, gap: 2 }}>
        <Text variante="corpsGras" couleur={danger ? colors.danger : undefined}>{titre}</Text>
        {sousTitre ? <Text variante="legende" muted>{sousTitre}</Text> : null}
      </View>
      {droite ?? (onPress ? <ChevronRight size={20} color={colors.sable300} /> : null)}
    </View>
  );
  if (!onPress) return contenu(false);
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={titre} onPress={onPress}>
      {({ pressed }) => contenu(pressed)}
    </Pressable>
  );
}

/** Carte d'en-tête colorée (cobalt) avec motif en filigrane. */
export function CarteHero({ children }: { children: ReactNode }) {
  return (
    <View style={{ backgroundColor: colors.blue, borderRadius: rayon.cardL, padding: sp[5], overflow: "hidden", gap: sp[3], ...ombre.pop }}>
      <FondMotif sombre />
      {children}
    </View>
  );
}

/** Avatar à initiales (CDC §9.3 point 3) : couleur dérivée de l'identifiant, 8 teintes. */
const COULEURS_AVATAR = [colors.blue, colors.success, colors.danger, colors.blueHover, colors.night, colors.sable600, colors.success, colors.warning];
export function Avatar({ nom, id, taille = 56, surFondSombre = false }: { nom: string; id?: string; taille?: number; surFondSombre?: boolean }) {
  const initiales = nom.split(/\s+/).filter(Boolean).slice(0, 2).map((m) => m[0]?.toUpperCase() ?? "").join("") || "?";
  const graine = [...(id ?? nom)].reduce((s, ch) => (s * 31 + ch.charCodeAt(0)) >>> 0, 7);
  const fond = surFondSombre ? "rgba(255,255,255,0.18)" : COULEURS_AVATAR[graine % COULEURS_AVATAR.length];
  return (
    <View style={{ width: taille, height: taille, borderRadius: taille / 2, backgroundColor: fond, alignItems: "center", justifyContent: "center", borderWidth: surFondSombre ? 2 : 0, borderColor: "rgba(255,255,255,0.35)" }}>
      <Text style={{ color: colors.white, fontWeight: "800", fontSize: taille * 0.36 }}>{initiales}</Text>
    </View>
  );
}
