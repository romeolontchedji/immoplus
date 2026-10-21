import { forwardRef, useState } from "react";
import { Pressable, TextInput, View, type TextInputProps } from "react-native";
import { familleDe } from "@/ui/theme/polices";
import { colors, fs, sp } from "@/ui/theme/tokens";
import { Eye, EyeOff } from "lucide-react-native";
import { Text } from "./Text";

export type TextFieldProps = TextInputProps & {
  label: string;
  erreur?: string;
  aide?: string;
};

/** Champ de saisie fidèle au design system (label majuscule 12px gras, bordure douce, fond blanc). */
export const TextField = forwardRef<TextInput, TextFieldProps>(function TextField(
  { label, erreur, aide, style, ...rest },
  ref,
) {
  return (
    <View style={{ gap: 6, marginBottom: sp[3] }}>
      <Text
        style={{
          fontSize: 12,
          fontWeight: "800",
          color: colors.night,
          letterSpacing: 0.5,
          textTransform: "uppercase",
        }}
      >
        {label}
      </Text>
      <TextInput
        ref={ref}
        accessibilityLabel={label}
        placeholderTextColor={colors.textMuted}
        {...rest}
        style={[
          {
            minHeight: 52,
            borderWidth: 1.5,
            borderRadius: 14,
            paddingHorizontal: 16,
            fontSize: fs[16],
            fontFamily: familleDe("500"),
            color: colors.night,
            backgroundColor: colors.white,
            borderColor: erreur ? colors.danger : "rgba(15, 27, 61, 0.12)",
          },
          style,
        ]}
      />
      {erreur ? (
        <Text style={{ fontSize: 12, fontWeight: "600", color: colors.danger }}>{erreur}</Text>
      ) : aide ? (
        <Text style={{ fontSize: 12, color: colors.textMuted }}>{aide}</Text>
      ) : null}
    </View>
  );
});

export const PasswordField = forwardRef<TextInput, TextFieldProps>(function PasswordField(
  props,
  ref,
) {
  const [visible, setVisible] = useState(false);
  return (
    <View style={{ position: "relative" }}>
      <TextField
        ref={ref}
        autoCapitalize="none"
        autoCorrect={false}
        textContentType="password"
        {...props}
        secureTextEntry={!visible}
      />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
        onPress={() => setVisible((v) => !v)}
        style={{
          position: "absolute",
          right: 16,
          top: 36,
          height: 32,
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {visible ? (
          <EyeOff size={20} color={colors.textMuted} />
        ) : (
          <Eye size={20} color={colors.textMuted} />
        )}
      </Pressable>
    </View>
  );
});
