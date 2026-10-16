import type { ReactNode } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, View, type RefreshControlProps } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { OfflineBanner } from "./States";

type Props = {
  children: ReactNode;
  /** Contenu défilant (formulaires, fiches). Pour une liste, utiliser FlatList dans un `Screen scroll={false}`. */
  scroll?: boolean;
  refreshControl?: React.ReactElement<RefreshControlProps>;
  /** Pas de marge latérale : listes qui gèrent leur propre mise en page. */
  flush?: boolean;
  footer?: ReactNode;
};

/** Cadre standard d'un écran : zone sûre, bandeau hors connexion, défilement, clavier, action principale en bas (CDC §12.1). */
export function Screen({ children, scroll = false, refreshControl, flush = false, footer }: Props) {
  const { c } = useTheme();
  const corps = scroll ? (
    <ScrollView contentContainerStyle={{ padding: flush ? 0 : sp[4], gap: sp[4], flexGrow: 1 }} keyboardShouldPersistTaps="handled" refreshControl={refreshControl}>
      {children}
    </ScrollView>
  ) : (
    <View style={{ flex: 1, padding: flush ? 0 : sp[4], gap: sp[4] }}>{children}</View>
  );
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }} edges={["top", "left", "right", "bottom"]}>
      <OfflineBanner />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        {corps}
        {footer ? <View style={{ padding: sp[4], borderTopWidth: 1, borderTopColor: c.border, backgroundColor: c.surface }}>{footer}</View> : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
