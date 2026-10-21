import { View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { BadgeCheck, CalendarDays, Clock, House, Star } from "lucide-react-native";
import { dateCourte } from "@/lib/format";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { EnTetePage } from "@/ui/components/EnTetePage";
import { ListingCard } from "@/ui/components/ListingCard";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useProfilGerant } from "./queries";

function delai(min: number | null | undefined): string | null {
  if (min == null) return null;
  if (min < 60) return `Répond en ${Math.max(1, Math.round(min))} min environ`;
  const h = Math.round(min / 60);
  return h < 24 ? `Répond en ${h} h environ` : `Répond en ${Math.round(h / 24)} j environ`;
}

function Fait({ Icone, texte }: { Icone: typeof Star; texte: string }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
      <Icone size={16} color={colors.textMuted} />
      <Text variante="legende" muted>{texte}</Text>
    </View>
  );
}

/**
 * Profil public d'un gérant (plan v3, F) : nom, badge, ancienneté, délai de réponse, chambres en ligne et avis des
 * locataires. Jamais de numéro. Ouvert depuis la fiche d'une chambre et l'en-tête de la discussion.
 */
export function GerantScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const requete = useProfilGerant(id);
  return (
    <Screen scroll>
      <EnTetePage titre="Profil du gérant" retour />
      <QueryState query={requete}>
        {(g) => (
          <View style={{ gap: sp[5] }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: sp[4], padding: sp[4], borderRadius: rayon.card, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }}>
              <View style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: colors.blueSoft, alignItems: "center", justifyContent: "center" }}>
                <Text style={{ fontSize: 22, fontWeight: "800", color: colors.primary }}>{(g.name ?? "G").slice(0, 2).toUpperCase()}</Text>
              </View>
              <View style={{ flex: 1, gap: sp[1] }}>
                <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2], flexWrap: "wrap" }}>
                  <Text variante="titreSection">{g.name ?? "Gérant"}</Text>
                  {g.verified ? (
                    <View style={{ flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: colors.successBg, borderRadius: rayon.pilule, paddingHorizontal: sp[2], paddingVertical: 2 }}>
                      <BadgeCheck size={13} color={colors.successText} />
                      <Text style={{ fontSize: 12, fontWeight: "700", color: colors.successText }}>Vérifié</Text>
                    </View>
                  ) : null}
                </View>
                <Fait Icone={CalendarDays} texte={`Sur Immo+ depuis le ${dateCourte(g.member_since)}`} />
                {delai(g.median_response_min) ? <Fait Icone={Clock} texte={delai(g.median_response_min) as string} /> : null}
                <Fait Icone={House} texte={`${g.listings.length} chambre${g.listings.length > 1 ? "s" : ""} en ligne`} />
                <Fait Icone={Star} texte={g.reviews.count ? `${Number(g.reviews.average).toFixed(1).replace(".", ",")} / 5 · ${g.reviews.count} avis` : "Pas encore d'avis"} />
              </View>
            </View>
            <View style={{ gap: sp[3] }}>
              <Text variante="label" muted>Ses chambres</Text>
              {g.listings.length ? (
                g.listings.map((c) => <ListingCard key={c.id} annonce={c} onPress={() => router.push({ pathname: "/annonces/[ident]", params: { ident: c.slug } })} />)
              ) : (
                <Text muted>Aucune chambre en ligne pour l’instant.</Text>
              )}
            </View>
          </View>
        )}
      </QueryState>
    </Screen>
  );
}
