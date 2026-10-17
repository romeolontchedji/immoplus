import { createContext, useContext, type ReactNode } from "react";
import { clair, type Palette } from "./tokens";

type Theme = { c: Palette; sombre: boolean };

/**
 * Thème unique : clair, quel que soit le réglage du système. Le mode sombre rendait des textes illisibles (écrans
 * qui utilisent `colors.night` en dur sur un fond sombre) ; décision produit : fond blanc partout.
 * La taille de police du système est respectée (pas de `allowFontScaling={false}`).
 */
const THEME: Theme = { c: clair, sombre: false };
const Ctx = createContext<Theme>(THEME);

export function ThemeProvider({ children }: { children: ReactNode }) {
  return <Ctx.Provider value={THEME}>{children}</Ctx.Provider>;
}

export const useTheme = (): Theme => useContext(Ctx);
