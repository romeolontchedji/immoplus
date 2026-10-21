import { secure } from "@/storage/secure";
import { newId } from "@/lib/uuid";
import { apiEvents } from "./events";

/**
 * Jetons de la session. Le jeton d'accès (15 min) ne vit qu'en mémoire ; le jeton de rafraîchissement (30 jours,
 * lié à l'appareil, à rotation) est dans le coffre sécurisé. Le renouvellement est « à vol unique » : plusieurs
 * requêtes qui reçoivent 401 en même temps n'en déclenchent qu'un (le serveur tolère 60 s de grâce, mais on évite d'en abuser).
 */
export type Jetons = { access: string; refresh: string; expires_in: number };
type Renouveleur = (refresh: string) => Promise<Jetons | null>;

let acces: string | null = null;
let installation: string | null = null;
let enCours: Promise<boolean> | null = null;
let renouveleur: Renouveleur | null = null;

/** Branché par `client.ts` (évite une dépendance circulaire avec le client HTTP). */
export function brancherRenouveleur(f: Renouveleur): void {
  renouveleur = f;
}

export function accessToken(): string | null {
  return acces;
}

export async function installationId(): Promise<string> {
  if (installation) return installation;
  installation = (await secure.getInstallation()) ?? null;
  if (!installation) {
    installation = newId();
    await secure.setInstallation(installation);
  }
  return installation;
}

export async function storeTokens(j: Pick<Jetons, "access" | "refresh">): Promise<void> {
  acces = j.access;
  await secure.setRefresh(j.refresh);
}

export async function clearSession(): Promise<void> {
  acces = null;
  await secure.clearRefresh();
}

export async function hasRefreshToken(): Promise<boolean> {
  return (await secure.getRefresh()) !== null;
}

/** Renouvelle les jetons. Retourne faux (et prévient l'interface) si la session ne peut plus l'être. */
export function refreshTokens(): Promise<boolean> {
  if (enCours) return enCours;
  enCours = (async () => {
    try {
      const refresh = await secure.getRefresh();
      if (!refresh || !renouveleur) return false;
      const jetons = await renouveleur(refresh);
      if (!jetons) {
        await clearSession();
        apiEvents.emit("signed_out", "session_expiree");
        return false;
      }
      await storeTokens(jetons);
      return true;
    } catch {
      return false; // réseau coupé : la session reste, on réessaiera
    } finally {
      enCours = null;
    }
  })();
  return enCours;
}

/** Pour les tests : remet le module à zéro. */
export function _reinitialiser(): void {
  acces = null;
  installation = null;
  enCours = null;
  renouveleur = null;
}
