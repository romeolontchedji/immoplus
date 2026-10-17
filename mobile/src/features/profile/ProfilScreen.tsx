import { Alert, Pressable, View } from "react-native";
import { useRouter } from "expo-router";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { CIBLE_MIN, colors, rayon, sp } from "@/ui/theme/tokens";
import { useTheme } from "@/ui/theme/ThemeProvider";
import { Button } from "@/ui/components/Button";
import { QueryState } from "@/ui/components/States";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";
import { useMe } from "./queries";

// Icônes minimalistes SVG sous forme de caractères unicode Lucide-compatibles
// (pas d'emoji, conforme AGENTS.md §13 et DESIGN.md)
// On utilise des formes géométriques car lucide-react-native nécessite un perf check séparé
function IconeCarree({ couleur, fond, label }: { couleur: string; fond: string; label: string }) {
  return (
    <View
      accessibilityLabel={label}
      style={{
        width: 40,
        height: 40,
        borderRadius: 12,
        backgroundColor: fond,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Placeholder icône – à remplacer par l'icône Lucide une fois lucide-react-native intégré */}
      <View style={{ width: 18, height: 18, borderRadius: 4, backgroundColor: couleur, opacity: 0.85 }} />
    </View>
  );
}

type LigneMenuProps = {
  titre: string;
  aide?: string;
  href: string;
  iconeLabel: string;
};

/** Ligne de menu conforme à la maquette Profil : icône carré arrondi bleu pâle + texte + chevron › */
function LigneMenu({ titre, aide, href, iconeLabel }: LigneMenuProps) {
  const { c } = useTheme();
  const router = useRouter();
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push(href as never)}
      style={({ pressed }) => ({
        flexDirection: "row",
        alignItems: "center",
        gap: sp[4],
        minHeight: CIBLE_MIN + 8,
        paddingVertical: sp[3],
        paddingHorizontal: sp[4],
        backgroundColor: pressed ? c.divider : c.surface,
        borderRadius: rayon.card,
        marginBottom: sp[2],
        // Ombre subtile comme dans la maquette
        shadowColor: "#0F1B3D",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.04,
        shadowRadius: 8,
        elevation: 1,
      })}
    >
      <IconeCarree couleur={c.primary} fond={c.primarySoft} label={iconeLabel} />
      <View style={{ flex: 1, gap: 2 }}>
        <Text variante="corps">{titre}</Text>
        {aide ? <Text variante="legende" muted>{aide}</Text> : null}
      </View>
      {/* Chevron › */}
      <Text muted style={{ fontSize: 20, fontWeight: "300", lineHeight: 24 }}>›</Text>
    </Pressable>
  );
}

/**
 * Onglet Profil (EF-CPT-01 à EF-CPT-08).
 * Conforme à la maquette « Mobile · Profil et vérification@1x.png » :
 * - avatar bleu cobalt + initiales, badge statut sous le nom
 * - bandeau vert "Identité vérifiée" si gérant vérifié
 * - lignes de menu en cartes blanches avec icône carrée arrondie
 * - bouton "Se déconnecter" rouge pâle en bas
 */
export function ProfilScreen() {
  const { etat, fermer } = useSession();
  const { c } = useTheme();
  const requete = useMe();
  const router = useRouter();

  if (etat.statut !== "connecte") {
    return (
      <Screen scroll>
        <AuthRequired />
      </Screen>
    );
  }

  const user = etat.user;
  const initiales = user.full_name
    .split(" ")
    .slice(0, 2)
    .map((m) => m[0]?.toUpperCase() ?? "")
    .join("");
  const estGerant = user.role === "gerant";

  const deconnecter = () => {
    Alert.alert(
      "Déconnexion",
      "Tu seras déconnecté de ce compte.",
      [
        { text: t.commun.annuler, style: "cancel" },
        { text: "Se déconnecter", style: "destructive", onPress: () => void fermer() },
      ],
    );
  };

  return (
    <Screen scroll>
      {/* En-tête : titre + avatar côte à côte comme dans la maquette */}
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: sp[2] }}>
        <Text variante="titre">Profil</Text>
        {/* Avatar compact en haut à droite (maquette) */}
        <View
          style={{
            width: 44,
            height: 44,
            borderRadius: 22,
            backgroundColor: c.primary,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Text variante="legende" couleur="#FFFFFF" style={{ fontWeight: "800" }}>{initiales}</Text>
        </View>
      </View>

      {/* Identité : nom + rôle */}
      <QueryState query={requete}>
        {(me) => (
          <View style={{ flexDirection: "row", alignItems: "center", gap: sp[3], marginBottom: sp[4] }}>
            {/* Grand avatar */}
            <View
              style={{
                width: 56,
                height: 56,
                borderRadius: 28,
                backgroundColor: c.primary,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Text variante="sousTitre" couleur="#FFFFFF" style={{ fontWeight: "800" }}>{initiales}</Text>
            </View>
            <View style={{ gap: 2 }}>
              <Text variante="sousTitre">{me.full_name}</Text>
              {/* Badge "Gérant vérifié" vert sous le nom, comme dans la maquette */}
              {estGerant ? (
                <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
                  <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: c.succes }} />
                  <Text variante="legende" couleur={c.succesText}>Gérant vérifié</Text>
                </View>
              ) : (
                <Text variante="legende" muted>Locataire</Text>
              )}
            </View>
          </View>
        )}
      </QueryState>

      {/* Bandeau "Identité vérifiée" uniquement pour les gérants vérifiés (maquette) */}
      {estGerant ? (
        <View
          style={{
            padding: sp[4],
            borderRadius: rayon.card,
            backgroundColor: c.succesBg,
            marginBottom: sp[4],
            gap: 4,
          }}
        >
          <Text variante="corpsGras" couleur={c.succesText}>Identité vérifiée par Logeo</Text>
          <Text variante="legende" couleur={c.succesText}>
            Pièces validées. Ce badge rassure les étudiants.
          </Text>
        </View>
      ) : null}

      {/* Lignes de menu (conforme maquette : cartes blanches individuelles) */}
      {estGerant ? (
        <LigneMenu titre="Mes chambres" href="/pro/annonces" iconeLabel="Mes chambres" />
      ) : (
        <>
          <LigneMenu titre="Mon compte" aide="Nom, téléphone, mot de passe" href="/parametres/nom" iconeLabel="Compte" />
          <LigneMenu titre="Appareils connectés" href="/parametres/appareils" iconeLabel="Appareils" />
        </>
      )}
      <LigneMenu titre="Notifications" href="/parametres/preferences" iconeLabel="Notifications" />
      <LigneMenu titre="Aide et contact" href="/parametres/aide" iconeLabel="Aide" />
      <LigneMenu titre="Conditions d'utilisation" href="/legal/conditions" iconeLabel="Conditions" />
      <LigneMenu titre="Politique de confidentialité" href="/legal/confidentialite" iconeLabel="Confidentialité" />

      {/* Bouton Se déconnecter : rouge pâle, texte rouge (conforme maquette) */}
      <Pressable
        accessibilityRole="button"
        onPress={deconnecter}
        style={({ pressed }) => ({
          minHeight: CIBLE_MIN,
          borderRadius: rayon.card,
          backgroundColor: pressed ? "#FCCFCF" : "#FFE8E8",
          alignItems: "center",
          justifyContent: "center",
          marginTop: sp[2],
        })}
      >
        <Text variante="corpsGras" couleur={c.danger}>Se déconnecter</Text>
      </Pressable>

      {/* Lien suppression discret */}
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push("/parametres/supprimer" as never)}
        style={{ alignItems: "center", padding: sp[4] }}
      >
        <Text variante="legende" couleur={c.danger}>Supprimer mon compte</Text>
      </Pressable>
    </Screen>
  );
}
