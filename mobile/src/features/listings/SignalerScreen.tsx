import { useState } from "react";
import { Pressable, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { CIBLE_MIN, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { Screen } from "@/ui/components/Screen";
import { TextField } from "@/ui/components/TextField";
import { Text } from "@/ui/components/Text";
import { useSignaler, useSignalerDejaLouee } from "./queries";
import type { components } from "@/api/genere/api";

type CodeMotif = components["schemas"]["SignalementIn"]["reason_code"];

type Motif = { code: CodeMotif; label: string; description: string };

const MOTIFS: Motif[] = [
  { code: "false_info", label: "Informations incorrectes", description: "Photos ou description ne correspondent pas à la réalité." },
  { code: "already_rented", label: "Chambre déjà louée", description: "Cette chambre n'est plus disponible mais l'annonce reste en ligne." },
  { code: "contact_outside", label: "Coordonnées partagées", description: "Le gérant partage son numéro ou demande à sortir de Logeo." },
  { code: "fraud", label: "Fraude ou arnaque", description: "Demande d'acompte sans visite, identité douteuse ou autre abus." },
  { code: "inappropriate", label: "Contenu inapproprié", description: "Photos ou texte offensants, discriminatoires ou hors sujet." },
  { code: "other", label: "Autre raison", description: "Décris le problème dans le champ ci-dessous." },
];

/**
 * Modale de signalement (EF-MOD-01) : sélection d'un motif + détails facultatifs.
 * Paramètres d'URL attendus : `type` (listing|message|conversation|user) et `id`.
 */
export function SignalerScreen() {
  const { c } = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ type?: string; id?: string }>();
  const type = (params.type ?? "listing") as "listing" | "message" | "conversation" | "user";
  const id = params.id ?? "";

  const [motif, setMotif] = useState<CodeMotif | null>(null);
  const [details, setDetails] = useState("");
  const signaler = useSignaler();
  const dejaLouee = useSignalerDejaLouee();

  const soumettre = () => {
    if (!motif) return;
    if (motif === "already_rented" && type === "listing") {
      dejaLouee.mutate(id, { onSuccess: () => router.back() });
    } else {
      signaler.mutate(
        { cible: type, id, motif, details: details.trim() || undefined },
        { onSuccess: () => router.back() },
      );
    }
  };

  const erreur = signaler.error ?? dejaLouee.error;
  const chargement = signaler.isPending || dejaLouee.isPending;

  return (
    <Screen
      scroll
      footer={
        <Button
          titre="Envoyer le signalement"
          chargement={chargement}
          disabled={!motif}
          onPress={soumettre}
        />
      }
    >
      <Text variante="titre">Signaler</Text>
      <Text muted>Ton signalement est anonyme et traité par notre équipe de modération sous 24 heures.</Text>

      {/* Liste des motifs */}
      <View style={{ gap: sp[2] }}>
        {MOTIFS.map((m) => (
          <Pressable
            key={m.code}
            accessibilityRole="radio"
            accessibilityState={{ selected: motif === m.code }}
            onPress={() => setMotif(m.code)}
            style={({ pressed }) => ({
              flexDirection: "row",
              alignItems: "flex-start",
              gap: sp[3],
              padding: sp[4],
              borderRadius: 14,
              borderWidth: 1.5,
              borderColor: motif === m.code ? c.primary : c.border,
              backgroundColor: motif === m.code ? c.primarySoft : (pressed ? c.divider : c.surface),
              minHeight: CIBLE_MIN,
            })}
          >
            <View
              style={{
                width: 20,
                height: 20,
                borderRadius: 10,
                borderWidth: 2,
                borderColor: motif === m.code ? c.primary : c.borderStrong,
                backgroundColor: motif === m.code ? c.primary : "transparent",
                marginTop: 2,
              }}
            />
            <View style={{ flex: 1, gap: 2 }}>
              <Text variante="corpsGras" couleur={motif === m.code ? c.primary : c.text}>{m.label}</Text>
              <Text variante="legende" muted>{m.description}</Text>
            </View>
          </Pressable>
        ))}
      </View>

      {/* Détails */}
      <TextField
        label="Détails (facultatif)"
        value={details}
        onChangeText={setDetails}
        multiline
        numberOfLines={3}
      />

      {erreur ? (
        <Text variante="legende" couleur={c.danger} accessibilityLiveRegion="polite">
          {isApiError(erreur) ? messageErreur(erreur.code, erreur.message) : t.commun.erreurGenerique}
        </Text>
      ) : null}
    </Screen>
  );
}
