import { Alert, Share, View } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { BarChart3, CircleAlert, CircleCheck, Eye, FilePen, Image as IconeImage, PenLine, Share2, Video } from "lucide-react-native";
import { WEB_HOST } from "@/config/env";
import { isApiError } from "@/api/errors";
import { messageErreur, t } from "@/i18n/fr";
import { francs } from "@/lib/format";
import { colors, rayon, sp } from "@/ui/theme/tokens";
import { Button } from "@/ui/components/Button";
import { Badge } from "@/ui/components/Card";
import { GroupeListe, LigneListe } from "@/ui/components/Groupe";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { type AnnoncePro, useActionAnnonce, useAnnoncePro, useMediasPro, usePreparation, useSupprimerAnnonce } from "./queries";
import { PHOTOS_MIN } from "./brouillon";
import { RAISONS_MASQUAGE, STATUTS } from "./statuts";

type Action = "confirm" | "hide" | "mark-rented" | "undo-rented" | "publish";

/** Ce qui empêche la publication, avec les mêmes libellés que le site (EF-ANN-09). */
function Preparation({ id }: { id: string }) {
  const requete = usePreparation(id);
  if (!requete.data || requete.data.publishable) return null;
  return (
    <View style={{ backgroundColor: colors.warningBg, borderRadius: rayon.card, padding: sp[4], gap: sp[2] }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: sp[2] }}>
        <CircleAlert size={18} color={colors.warningText} />
        <Text variante="corpsGras" couleur={colors.warningText}>Pour publier, il manque :</Text>
      </View>
      {requete.data.missing.map((m) => (
        <Text key={m.code} variante="legende" couleur={colors.warningText}>• {m.label}</Text>
      ))}
    </View>
  );
}

function Medias({ id, onCompleter }: { id: string; onCompleter: () => void }) {
  const requete = useMediasPro(id);
  const liste = requete.data ?? [];
  const pret = (k: string) => liste.filter((m) => m.kind === k && m.status === "ready").length;
  const enCours = liste.filter((m) => ["pending", "uploading", "processing"].includes(m.status)).length;
  return (
    <GroupeListe titre="Photos et vidéo">
      <LigneListe titre="Vidéo" sousTitre={pret("video") ? "Prête" : "Facultative : elle attire plus de contacts"} icone={Video} teinte={pret("video") ? "vert" : "bleu"} onPress={onCompleter} />
      <LigneListe titre="Photos" sousTitre={`${pret("photo")} prête(s) · ${PHOTOS_MIN} au minimum`} icone={IconeImage} teinte={pret("photo") >= PHOTOS_MIN ? "vert" : "soleil"} onPress={onCompleter} />
      {enCours ? <LigneListe titre={`${enCours} média(s) en traitement`} sousTitre="Ça prend quelques minutes, tu peux fermer l'app." icone={CircleCheck} teinte="gris" /> : null}
    </GroupeListe>
  );
}

/** Actions possibles selon le statut (EF-ANN-10 à 14). */
function actionsPour(a: AnnoncePro): { action: Action; titre: string; variante?: "secondaire" | "fantome"; confirmer?: string }[] {
  switch (a.status) {
    case "published":
      // « Confirmer qu'elle est libre » retiré (plan v3, D1) : louée ou masquée, le gérant le dit lui-même.
      return [
        { action: "mark-rented", titre: "Marquer comme louée", confirmer: "Elle disparaîtra des recherches. Les conversations restent ; la vidéo sera supprimée dans 7 jours sauf annulation." },
        { action: "hide", titre: "Masquer", variante: "fantome" },
      ];
    case "hidden":
      return [{ action: "publish", titre: "Remettre en ligne" }];
    case "rented":
      return [{ action: "undo-rented", titre: "Annuler « louée »", variante: "secondaire" }];
    case "draft":
    case "processing":
      return [{ action: "publish", titre: "Publier" }];
    default:
      return [];
  }
}

/** Détail d'une annonce côté gérant (plan v2, MM5) : statut, manques, médias, actions, accès à la modification et aux statistiques. */
export function AnnonceGerantScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const requete = useAnnoncePro(id);
  const action = useActionAnnonce(id);
  const supprimer = useSupprimerAnnonce(id);
  const demanderSuppression = () =>
    Alert.alert("Supprimer l'annonce ?", "Elle disparaîtra pour tout le monde. Les conversations restent lisibles.", [
      { text: t.commun.annuler, style: "cancel" },
      { text: "Supprimer", style: "destructive", onPress: () => supprimer.mutate(undefined, { onSuccess: () => router.replace("/pro/annonces" as never) }) },
    ]);

  const lancer = (a: Action, confirmer?: string) => {
    if (!confirmer) return action.mutate(a);
    Alert.alert("Confirmer", confirmer, [{ text: t.commun.annuler, style: "cancel" }, { text: "Confirmer", onPress: () => action.mutate(a) }]);
  };

  return (
    <Screen scroll>
      <QueryState query={requete}>
        {(a) => {
          const statut = STATUTS[a.status] ?? { libelle: a.status, ton: "neutre" as const };
          return (
            <>
              <View style={{ gap: sp[2] }}>
                {a.status === "draft" ? (
                  <View style={{ flexDirection: "row", gap: sp[2], alignItems: "flex-start", padding: sp[3], borderRadius: rayon.card, borderWidth: 2, borderStyle: "dashed", borderColor: colors.sun, backgroundColor: colors.warningBg }}>
                    <FilePen size={18} color={colors.warning} />
                    <Text style={{ flex: 1 }} variante="legende">
                      <Text variante="legende" style={{ fontWeight: "800" }}>Brouillon</Text> · pas encore visible par les locataires. Termine-la puis publie-la.
                    </Text>
                  </View>
                ) : (
                  <Badge titre={statut.libelle} ton={statut.ton} style={{ alignSelf: "flex-start" }} />
                )}
                <Text variante="titre">{a.title}</Text>
                <Text muted>{[a.room_type_label, a.district_name, `${francs(a.rent_amount)} / mois${a.rent_negotiable ? " · à débattre" : ""}`].filter(Boolean).join(" · ")}</Text>
                {a.status !== "draft" ? <Text variante="legende" muted>{`${a.views_total} vue${a.views_total > 1 ? "s" : ""} depuis la publication`}</Text> : null}
                {a.status === "hidden" && a.hidden_reason ? <Text variante="legende" couleur={colors.warningText}>{RAISONS_MASQUAGE[a.hidden_reason] ?? "Annonce masquée."}</Text> : null}
              </View>

              {["draft", "processing", "hidden"].includes(a.status) ? <Preparation id={a.id} /> : null}

              <View style={{ gap: sp[2] }}>
                {actionsPour(a).map((x) => (
                  <Button key={x.action} titre={x.titre} variante={x.variante} chargement={action.isPending && action.variables === x.action} onPress={() => lancer(x.action, x.confirmer)} />
                ))}
                {action.error ? (
                  <Text variante="legende" couleur={colors.danger} accessibilityLiveRegion="polite">
                    {isApiError(action.error) ? messageErreur(action.error.code, action.error.message) : t.erreurs.network}
                  </Text>
                ) : null}
              </View>

              <Medias id={a.id} onCompleter={() => router.push(`/pro/nouvelle-annonce/medias?annonce=${a.id}` as never)} />

              <GroupeListe titre="Gérer">
                <LigneListe titre="Modifier l'annonce" sousTitre="Titre, loyer, quartier, description…" icone={PenLine} onPress={() => router.push(`/pro/annonce/${a.id}/modifier` as never)} />
                <LigneListe titre="Statistiques" sousTitre="Vues, favoris et contacts" icone={BarChart3} onPress={() => router.push(`/pro/annonce/${a.id}/stats` as never)} />
                {a.status === "published" ? (
                  <LigneListe
                    titre="Partager l'annonce"
                    sousTitre="WhatsApp, Facebook, TikTok ou lien à copier"
                    icone={Share2}
                    teinte="soleil"
                    onPress={() => {
                      const lien = `https://${WEB_HOST}/annonces/${a.slug}`;
                      void Share.share({ title: a.title, message: `${a.title}, ${francs(a.rent_amount)}/mois sur Immo+\n${lien}`, url: lien });
                    }}
                  />
                ) : null}
                {a.status === "published" ? (
                  <LigneListe titre="Voir comme un locataire" icone={Eye} onPress={() => router.push({ pathname: "/annonces/[ident]", params: { ident: a.slug } })} />
                ) : null}
              </GroupeListe>

              {a.status !== "removed" ? (
                <View style={{ gap: sp[2] }}>
                  <Button titre={a.status === "draft" ? "Supprimer le brouillon" : "Supprimer l'annonce"} variante="danger" chargement={supprimer.isPending} onPress={demanderSuppression} />
                  {supprimer.error ? (
                    <Text variante="legende" couleur={colors.danger}>{isApiError(supprimer.error) ? messageErreur(supprimer.error.code, supprimer.error.message) : t.erreurs.network}</Text>
                  ) : null}
                </View>
              ) : null}
            </>
          );
        }}
      </QueryState>
    </Screen>
  );
}
