import { jetons } from "./jetons.genere";

/**
 * Jetons de design de l'application Logeo.
 * Source unique : docs/design/tokens.json → jetons.genere.ts (couleurs, espaces, rayons, tailles), partagée avec le site.
 */

const c = jetons.couleurs;

/** Couleurs : générées depuis docs/design/tokens.json (outils/construire_tokens.py), noms historiques conservés. */
export const colors = {
  primary: c.blue,
  blue: c.blue,
  blueHover: c.blueHover,
  blueSoft: c.blueSoft,
  sun: c.sun,
  sunHover: c.sunHover,
  night: c.night,
  sable300: c.sable300,
  sable600: c.sable600,
  sable950: c.sable950,
  textMuted: c.sable600,
  bg: c.bg,
  surface: c.surface,
  border: c.border,
  divider: c.divider,
  success: c.success,
  successBg: c.successBg,
  successText: c.success,
  warning: c.warning,
  warningBg: c.warningBg,
  warningText: c.warning,
  danger: c.danger,
  dangerBg: c.dangerBg,
  dangerText: c.danger,
  white: c.white,
} as const;

export type Palette = {
  bg: string;
  surface: string;
  surfaceRaised: string;
  surfaceSunken: string;
  border: string;
  borderStrong: string;
  divider: string;
  text: string;
  textMuted: string;
  primary: string;
  primaryHover: string;
  onPrimary: string;
  primarySoft: string;
  onPrimarySoft: string;
  accent: string;
  accentHover: string;
  onAccent: string;
  link: string;
  focus: string;
  scrim: string;
  succes: string;
  succesBg: string;
  succesText: string;
  avertissement: string;
  avertissementBg: string;
  avertissementText: string;
  danger: string;
  dangerBg: string;
  dangerText: string;
  information: string;
  informationBg: string;
  informationText: string;
};

export const clair: Palette = {
  bg: colors.bg,
  surface: colors.surface,
  surfaceRaised: colors.surface,
  surfaceSunken: colors.bg,
  border: colors.border,
  borderStrong: c.borderStrong,
  divider: colors.divider,
  text: colors.night,
  textMuted: colors.textMuted,
  primary: colors.blue,
  primaryHover: colors.blueHover,
  onPrimary: colors.white,
  primarySoft: colors.blueSoft,
  onPrimarySoft: colors.blue,
  accent: colors.sun,
  accentHover: colors.sunHover,
  onAccent: colors.night,
  link: colors.blue,
  focus: colors.blue,
  scrim: "rgba(15, 27, 61, 0.70)",
  succes: colors.success,
  succesBg: colors.successBg,
  succesText: colors.successText,
  avertissement: colors.warning,
  avertissementBg: colors.warningBg,
  avertissementText: colors.warningText,
  danger: colors.danger,
  dangerBg: colors.dangerBg,
  dangerText: colors.dangerText,
  information: colors.blue,
  informationBg: colors.blueSoft,
  informationText: colors.blue,
};

/** Grille de 4 dp. */
export const sp = jetons.espaces;

/** Rayons conformes à DESIGN.md §3 */
export const rayon = {
  field: jetons.rayons.field,
  card: jetons.rayons.card,
  cardL: jetons.rayons.cardL,
  sheet: jetons.rayons.sheet,
  pilule: jetons.rayons.pill,
  // Alias de compatibilité
  1: 8,
  2: jetons.rayons.field,
  3: jetons.rayons.card,
  4: jetons.rayons.cardL,
} as const;

/** Typographie (DESIGN.md §3) */
export const fs = jetons.tailles;

/** Ombres subtiles */
export const ombre = {
  card: {
    shadowColor: "#0F1B3D",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 16,
    elevation: 3,
  },
  pop: {
    shadowColor: "#0F1B3D",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.18,
    shadowRadius: 40,
    elevation: 8,
  },
} as const;

/** Cible tactile minimale (ENF-ACC-01 : 48 dp). */
export const CIBLE_MIN = 48;
