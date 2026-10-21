import { Pressable, ScrollView, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ShieldCheck, Shield } from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api, unwrap } from "@/api/client";
import type { components } from "@/api/genere/api";
import { t } from "@/i18n/fr";
import { ErrorState } from "@/ui/components/States";
import { Skeleton } from "@/ui/components/Skeleton";
import { Text } from "@/ui/components/Text";
import { colors, ombre, rayon, sp } from "@/ui/theme/tokens";

type Document = components["schemas"]["DocumentLegalOut"];
type Slug = Document["slug"];

const SOUS_TITRE: Record<Slug, string> = { conditions: "Règles d’utilisation de Immo+", confidentialite: "Tes données et tes droits" };

function useDocumentLegal(slug: Slug) {
  return useQuery({
    queryKey: ["legal", slug],
    queryFn: () => unwrap(api.GET("/v1/legal/{slug}", { params: { path: { slug } } })),
    staleTime: 60 * 60_000,
  });
}

function dateLisible(iso: string): string {
  const [a, m, j] = iso.split("-").map(Number);
  const mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  return a && m && j ? `${j} ${mois[m - 1]} ${a}` : iso;
}

/** Conditions d'utilisation et politique de confidentialité : même texte que le site (GET /v1/legal/{slug}). */
export function LegalScreen() {
  const router = useRouter();
  const { slug: brut } = useLocalSearchParams<{ slug: string }>();
  const slug: Slug = brut === "confidentialite" ? "confidentialite" : "conditions";
  const requete = useDocumentLegal(slug);
  const doc = requete.data;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={["top", "bottom"]}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: sp[3], paddingHorizontal: sp[4], paddingVertical: sp[3] }}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t.commun.retour}
          onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))}
          style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center" }}
        >
          <ArrowLeft size={20} color={colors.night} />
        </Pressable>
        <View style={{ flex: 1 }}>
          <Text variante="sousTitre" numberOfLines={1}>{doc?.title ?? (slug === "conditions" ? "Conditions d’utilisation" : "Politique de confidentialité")}</Text>
          <Text variante="legende" muted>{SOUS_TITRE[slug]}</Text>
        </View>
      </View>

      {requete.isError ? (
        <ErrorState erreur={requete.error} onRetry={() => void requete.refetch()} />
      ) : !doc ? (
        <View style={{ padding: sp[4], gap: sp[3] }}>
          <Skeleton hauteur={180} />
          <Skeleton hauteur={140} />
          <Skeleton hauteur={140} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: sp[4], gap: sp[4], paddingBottom: sp[10] }}>
          <View style={{ backgroundColor: colors.primary, borderRadius: rayon.cardL, padding: sp[5], gap: sp[3], ...ombre.pop }}>
            <View style={{ flexDirection: "row", gap: sp[3], alignItems: "center" }}>
              <View style={{ width: 48, height: 48, borderRadius: 24, backgroundColor: "rgba(255,255,255,0.16)", alignItems: "center", justifyContent: "center" }}>
                <ShieldCheck size={24} color={colors.white} />
              </View>
              <Text style={{ flex: 1, color: colors.white, fontSize: 20, lineHeight: 26, fontWeight: "800" }}>{doc.editor.company}</Text>
            </View>
            <Text style={{ color: colors.white, fontSize: 15, lineHeight: 22 }}>{doc.summary}</Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
              {[`Mise à jour : ${dateLisible(doc.updated_at)}`, `RCCM : ${doc.editor.rccm}`, `IFU : ${doc.editor.ifu}`, "Parakou, Bénin"].map((p) => (
                <View key={p} style={{ paddingHorizontal: sp[3], paddingVertical: 5, borderRadius: rayon.pilule, backgroundColor: "rgba(255,255,255,0.14)", borderWidth: 1, borderColor: "rgba(255,255,255,0.28)" }}>
                  <Text style={{ color: colors.white, fontSize: 12, fontWeight: "700" }}>{p}</Text>
                </View>
              ))}
            </View>
          </View>

          {doc.provisional ? (
            <View style={{ padding: sp[3], borderRadius: rayon.field, backgroundColor: colors.warningBg }}>
              <Text variante="legende" couleur={colors.warningText} style={{ fontWeight: "700" }}>
                Version provisoire : l’identité de l’éditeur sera complétée avant l’ouverture officielle.
              </Text>
            </View>
          ) : null}

          {doc.sections.map((s) => (
            <View key={s.title} style={{ backgroundColor: colors.surface, borderRadius: rayon.card, borderWidth: 1, borderColor: colors.border, padding: sp[5], gap: sp[3] }}>
              <Text variante="sousTitre">{s.title}</Text>
              {s.blocks.map((b, i) =>
                b.type === "li" ? (
                  <View key={i} style={{ flexDirection: "row", gap: sp[3] }}>
                    <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: colors.primary, marginTop: 9 }} />
                    <Text muted style={{ flex: 1, lineHeight: 22 }}>
                      {b.label ? <Text style={{ fontWeight: "800", color: colors.night }}>{`${b.label} : `}</Text> : null}
                      {b.text}
                    </Text>
                  </View>
                ) : (
                  <Text key={i} muted style={{ lineHeight: 22 }}>{b.text}</Text>
                ),
              )}
            </View>
          ))}

          <View style={{ flexDirection: "row", gap: sp[3], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.blueSoft }}>
            <Shield size={18} color={colors.primary} />
            <Text variante="legende" muted style={{ flex: 1, fontWeight: "600", lineHeight: 19 }}>
              {`${doc.editor.company} — RCCM : ${doc.editor.rccm} — IFU : ${doc.editor.ifu} — ${doc.editor.address} — ${doc.editor.email}`}
            </Text>
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
