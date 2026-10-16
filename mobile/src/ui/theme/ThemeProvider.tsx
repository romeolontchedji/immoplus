import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useColorScheme } from "react-native";
import { clair, sombre, type Palette } from "./tokens";

type Theme = { c: Palette; sombre: boolean };
const Ctx = createContext<Theme>({ c: clair, sombre: false });

/** Thème clair/sombre selon le réglage du système. La taille de police du système est respectée (pas de `allowFontScaling={false}`). */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const schema = useColorScheme();
  const valeur = useMemo<Theme>(() => ({ c: schema === "dark" ? sombre : clair, sombre: schema === "dark" }), [schema]);
  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

export const useTheme = (): Theme => useContext(Ctx);
