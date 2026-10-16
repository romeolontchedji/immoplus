/**
 * Jetons de design de l'application Logeo.
 * Source unique de vérité : docs/design/DESIGN.md §3 et serveur/web/static/css/tokens.css.
 */

export const colors = {
  primary: "#1B44D6",
  blue: "#1B44D6",
  blueHover: "#1538B8",
  blueSoft: "#EAF0FF",
  sun: "#FFB429",
  sunHover: "#E8A320",
  night: "#0F1B3D",
  sable300: "#94A3B8",
  sable600: "#4A5373",
  sable950: "#0B132B",
  textMuted: "#4A5373",
  bg: "#F5F6FA",
  surface: "#FFFFFF",
  border: "#D5DAEA",
  divider: "#EDEFF6",
  success: "#12805C",
  successBg: "#DDF3EA",
  successText: "#0C6B4A",
  warning: "#8A5300",
  warningBg: "#FFF0D2",
  warningText: "#8A5300",
  danger: "#A32218",
  dangerBg: "#FBE1DE",
  dangerText: "#A32218",
  white: "#FFFFFF",
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
  borderStrong: "#B8C4D9",
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

export const sombre: Palette = {
  bg: colors.sable950,
  surface: colors.night,
  surfaceRaised: "#1A264F",
  surfaceSunken: "#060B1A",
  border: "#2D3A63",
  borderStrong: "#4A5B8C",
  divider: "#1E2B52",
  text: "#F1F5F9",
  textMuted: colors.sable300,
  primary: "#3B82F6",
  primaryHover: "#60A5FA",
  onPrimary: colors.sable950,
  primarySoft: "#172554",
  onPrimarySoft: "#93C5FD",
  accent: colors.sun,
  accentHover: colors.sunHover,
  onAccent: colors.night,
  link: "#60A5FA",
  focus: "#60A5FA",
  scrim: "rgba(0, 0, 0, 0.70)",
  succes: "#10B981",
  succesBg: "#064E3B",
  succesText: "#A7F3D0",
  avertissement: "#F59E0B",
  avertissementBg: "#78350F",
  avertissementText: "#FDE68A",
  danger: "#EF4444",
  dangerBg: "#7F1D1D",
  dangerText: "#FECACA",
  information: "#3B82F6",
  informationBg: "#1E3A8A",
  informationText: "#BFDBFE",
};

/** Grille de 4 dp. */
export const sp = {
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  14: 56,
} as const;

/** Rayons conformes à DESIGN.md §3 */
export const rayon = {
  field: 14,
  card: 20,
  cardL: 24,
  sheet: 28,
  pilule: 999,
  // Alias de compatibilité
  1: 8,
  2: 14,
  3: 20,
  4: 24,
} as const;

/** Typographie (DESIGN.md §3) */
export const fs = {
  12: 12,
  13: 13,
  14: 14,
  15: 15,
  16: 16,
  17: 17,
  18: 18,
  20: 20,
  24: 24,
  26: 26,
  28: 28,
  30: 30,
} as const;

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
