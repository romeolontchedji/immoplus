import { forwardRef, useState } from "react";
import { Pressable, TextInput, View, type TextInputProps } from "react-native";
import { colors, fs, rayon, sp } from "@/ui/theme/tokens";
import { formaterLocal } from "@/lib/phone";
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
            color: colors.night,
            backgroundColor: "#FFFFFF",
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

/** Numéro béninois : préfixe +229 fixe et champ groupé conforme aux maquettes. */
export const PhoneField = forwardRef<
  TextInput,
  Omit<TextFieldProps, "label"> & { label?: string }
>(function PhoneField({ label = "NUMÉRO DE TÉLÉPHONE", value, onChangeText, erreur, aide, ...rest }, ref) {
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
      <View style={{ flexDirection: "row", gap: 10 }}>
        <View
          style={{
            minHeight: 52,
            justifyContent: "center",
            alignItems: "center",
            paddingHorizontal: 16,
            borderRadius: 14,
            backgroundColor: "#FFFFFF",
            borderWidth: 1.5,
            borderColor: "rgba(15, 27, 61, 0.12)",
          }}
        >
          <Text style={{ fontSize: fs[16], fontWeight: "700", color: colors.night }}>+229</Text>
        </View>
        <TextInput
          ref={ref}
          accessibilityLabel={label}
          keyboardType="phone-pad"
          autoComplete="tel"
          textContentType="telephoneNumber"
          placeholder="01 97 42 18 06"
          placeholderTextColor={colors.textMuted}
          maxLength={14}
          value={formaterLocal(String(value ?? ""))}
          onChangeText={(v) => onChangeText?.(formaterLocal(v))}
          {...rest}
          style={{
            flex: 1,
            minHeight: 52,
            borderWidth: 1.5,
            borderRadius: 14,
            paddingHorizontal: 16,
            fontSize: fs[16],
            fontWeight: "600",
            color: colors.night,
            backgroundColor: "#FFFFFF",
            borderColor: erreur ? colors.danger : "rgba(15, 27, 61, 0.12)",
          }}
        />
      </View>
      {erreur ? (
        <Text style={{ fontSize: 12, fontWeight: "600", color: colors.danger }}>{erreur}</Text>
      ) : aide ? (
        <Text style={{ fontSize: 12, color: colors.textMuted }}>{aide}</Text>
      ) : null}
    </View>
  );
});
