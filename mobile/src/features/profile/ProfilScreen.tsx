import { Alert, Linking, Switch, View } from "react-native";
import { useRouter } from "expo-router";
import {
  Bell,
  Building2,
  FileText,
  Fingerprint,
  Gauge,
  Heart,
  KeyRound,
  LifeBuoy,
  LogOut,
  MessageCircle,
  ShieldCheck,
  Smartphone,
  UserRound,
  BellRing,
} from "lucide-react-native";
import { AuthRequired } from "@/features/auth/AuthRequired";
import { OCCUPATIONS } from "@/features/auth/ChoixOccupation";
import { useVerrouBiometrique } from "@/features/auth/verrou";
import { useContactEquipe } from "@/features/system/useAppConfig";
import { APP_VERSION } from "@/config/env";
import { formaterLocal } from "@/lib/phone";
import { t } from "@/i18n/fr";
import { useSession } from "@/state/session";
import { colors, sp } from "@/ui/theme/tokens";
import { Avatar, CarteHero, GroupeListe, LigneListe } from "@/ui/components/Groupe";
import { EnTetePage } from "@/ui/components/EnTetePage";
import { Screen } from "@/ui/components/Screen";
import { Text } from "@/ui/components/Text";

/**
 * Onglet Profil (EF-CPT-01 à 08), style « épuré » des captures (plan d'actions v2, M7) : carte d'identité cobalt,
 * listes groupées « Compte et sécurité », « Mon activité », « Préférences et assistance », « Informations légales ».
 */
export function ProfilScreen() {
  const { etat, fermer } = useSession();
  const router = useRouter();
  const equipe = useContactEquipe();
  const verrou = useVerrouBiometrique(); // ADR 0005 : ligne affichée seulement si le téléphone a une empreinte

  if (etat.statut !== "connecte") {
    return (
      <Screen scroll>
        <AuthRequired />
      </Screen>
    );
  }

  const user = etat.user;
  const estGerant = user.role === "gerant";
  const occupation = OCCUPATIONS.find((o) => o.valeur === user.occupation)?.libelle;
  const aller = (href: string) => () => router.push(href as never);

  const deconnecter = () =>
    Alert.alert("Déconnexion", "Tu seras déconnecté de ce compte.", [
      { text: t.commun.annuler, style: "cancel" },
      { text: "Se déconnecter", style: "destructive", onPress: () => void fermer() },
    ]);

  return (
    <Screen scroll>
      <EnTetePage titre="Profil" />

      <CarteHero>
        <View style={{ flexDirection: "row", alignItems: "center", gap: sp[4] }}>
          <Avatar nom={user.full_name} id={user.id} taille={60} surFondSombre />
          <View style={{ flex: 1, gap: 2 }}>
            <Text variante="sousTitre" couleur={colors.white}>{user.full_name}</Text>
            {user.phone ? <Text variante="legende" couleur="rgba(255,255,255,0.82)">+229 {formaterLocal(user.phone.replace(/^\+229/, ""))}</Text> : null}
          </View>
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: sp[2] }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "rgba(255,255,255,0.16)", paddingHorizontal: sp[3], paddingVertical: 6, borderRadius: 999 }}>
            <ShieldCheck size={14} color={colors.white} />
            <Text variante="legende" couleur={colors.white} style={{ fontWeight: "700" }}>{estGerant ? "Compte gérant" : "Numéro vérifié"}</Text>
          </View>
          {occupation ? (
            <View style={{ backgroundColor: "rgba(255,255,255,0.16)", paddingHorizontal: sp[3], paddingVertical: 6, borderRadius: 999 }}>
              <Text variante="legende" couleur={colors.white} style={{ fontWeight: "700" }}>{occupation}</Text>
            </View>
          ) : null}
        </View>
      </CarteHero>

      <GroupeListe titre="Compte et sécurité">
        <LigneListe titre="Mon profil" sousTitre="Nom, « Tu es »" icone={UserRound} onPress={aller("/parametres/nom")} />
        <LigneListe titre="Numéro de téléphone" icone={Smartphone} onPress={aller("/parametres/telephone")} />
        <LigneListe titre="Mot de passe" icone={KeyRound} onPress={aller("/parametres/mot-de-passe")} />
        <LigneListe titre="Appareils connectés" sousTitre="Déconnecte un téléphone perdu" icone={ShieldCheck} onPress={aller("/parametres/appareils")} />
        {verrou.disponible ? (
          <LigneListe
            titre="Déverrouiller avec l’empreinte"
            sousTitre="À l’ouverture et après 5 min d’absence"
            icone={Fingerprint}
            droite={<Switch accessibilityLabel="Déverrouiller avec l’empreinte" value={verrou.actif} onValueChange={(v) => void (v ? verrou.activer() : verrou.desactiver())} trackColor={{ true: colors.primary, false: colors.border }} />}
          />
        ) : verrou.disponible === false ? (
          // Ligne visible même sans capteur prêt : on sait que la fonction existe et comment l'obtenir.
          <LigneListe
            titre="Déverrouiller avec l’empreinte"
            sousTitre="Enregistre d’abord une empreinte dans les réglages du téléphone"
            icone={Fingerprint}
            teinte="gris"
            droite={null}
          />
        ) : null}
      </GroupeListe>

      <GroupeListe titre="Mon activité">
        {estGerant ? (
          <LigneListe titre="Mes chambres" icone={Building2} teinte="soleil" onPress={aller("/pro/annonces")} />
        ) : (
          <LigneListe titre="Mes favoris" icone={Heart} teinte="rouge" onPress={aller("/favoris")} />
        )}
        {estGerant ? null : <LigneListe titre="Mes alertes" icone={BellRing} teinte="soleil" onPress={aller("/alertes")} />}
      </GroupeListe>

      <GroupeListe titre="Préférences et assistance">
        <LigneListe titre="Notifications" icone={Bell} onPress={aller("/parametres/preferences")} />
        <LigneListe titre="Économie de données" icone={Gauge} onPress={aller("/parametres/economie-donnees")} />
        <LigneListe titre="WhatsApp Immo+" sousTitre={equipe.affiche} icone={MessageCircle} teinte="vert" onPress={() => void Linking.openURL(equipe.whatsapp_url)} />
        <LigneListe titre="Aide et contact" icone={LifeBuoy} onPress={aller("/parametres/aide")} />
      </GroupeListe>

      <GroupeListe titre="Informations légales">
        <LigneListe titre="Conditions d’utilisation" icone={FileText} teinte="gris" onPress={aller("/legal/conditions")} />
        <LigneListe titre="Politique de confidentialité" icone={ShieldCheck} teinte="gris" onPress={aller("/legal/confidentialite")} />
      </GroupeListe>

      <GroupeListe>
        <LigneListe titre="Se déconnecter" icone={LogOut} danger onPress={deconnecter} droite={null} />
      </GroupeListe>

      <View style={{ alignItems: "center", gap: sp[2], paddingBottom: sp[4] }}>
        <Text variante="legende" couleur={colors.danger} onPress={aller("/parametres/supprimer")} accessibilityRole="link">Supprimer mon compte</Text>
        <Text variante="legende" muted>Immo+ · version {APP_VERSION}</Text>
      </View>
    </Screen>
  );
}
