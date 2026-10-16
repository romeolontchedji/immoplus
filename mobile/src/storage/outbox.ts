import { CLES_KV, kv } from "./kv";

/**
 * File d'envoi des messages (ENF-RES-01, ENF-RES-02). Chaque message reçoit son `client_msg_id` **à la création** : le
 * serveur est idempotent sur cet identifiant, donc renvoyer après un doute (réponse perdue) ne crée jamais de doublon.
 * La file survit au redémarrage de l'application ; elle est vidée à la déconnexion.
 */
export type ElementFile = {
  clientMsgId: string;
  conversationId: string;
  body: string;
  creeLe: number;
  etat: "en_attente" | "echec";
  /** Code d'erreur métier définitif (ex. `contact_detected`), pour expliquer l'échec. */
  codeErreur?: string;
  tentatives: number;
};

export type Envoyeur = (e: ElementFile) => Promise<void>;
/** Distingue « réessayer plus tard » (réseau, 429, 5xx) de « ça ne passera jamais » (4xx métier). */
export type Classeur = (erreur: unknown) => { reessayer: boolean; code?: string };

let file: ElementFile[] | null = null;
let enVol: Promise<void> | null = null;
const ecouteurs = new Set<() => void>();

async function charger(): Promise<ElementFile[]> {
  if (!file) file = (await kv.get<ElementFile[]>(CLES_KV.outbox)) ?? [];
  return file;
}
const VIDE: ElementFile[] = [];

async function sauver(): Promise<void> {
  file = [...(file ?? [])]; // nouvelle référence : les abonnés (useSyncExternalStore) voient le changement
  await kv.set(CLES_KV.outbox, file);
  ecouteurs.forEach((e) => e());
}

export const outbox = {
  /** Charge la file depuis le disque (à appeler au démarrage, avant le premier rendu des conversations). */
  async precharger(): Promise<void> {
    await charger();
    ecouteurs.forEach((e) => e());
  },
  /** Instantané synchrone pour `useSyncExternalStore` : référence stable tant que la file ne change pas. */
  instantane(): ElementFile[] {
    return file ?? VIDE;
  },
  async lister(conversationId?: string): Promise<ElementFile[]> {
    const tous = await charger();
    return conversationId ? tous.filter((e) => e.conversationId === conversationId) : [...tous];
  },
  async ajouter(e: Omit<ElementFile, "creeLe" | "etat" | "tentatives">, maintenant = Date.now()): Promise<ElementFile> {
    const element: ElementFile = { ...e, creeLe: maintenant, etat: "en_attente", tentatives: 0 };
    (await charger()).push(element);
    await sauver();
    return element;
  },
  async retirer(clientMsgId: string): Promise<void> {
    file = (await charger()).filter((e) => e.clientMsgId !== clientMsgId);
    await sauver();
  },
  /** Remet un message en échec dans la file (bouton « Renvoyer »). Même `client_msg_id` : toujours sans doublon. */
  async relancer(clientMsgId: string): Promise<void> {
    const e = (await charger()).find((x) => x.clientMsgId === clientMsgId);
    if (e) {
      e.etat = "en_attente";
      e.codeErreur = undefined;
      await sauver();
    }
  },
  async vider(): Promise<void> {
    file = [];
    await kv.remove(CLES_KV.outbox);
    ecouteurs.forEach((e) => e());
  },
  abonner(ecouteur: () => void): () => void {
    ecouteurs.add(ecouteur);
    return () => void ecouteurs.delete(ecouteur);
  },
  /**
   * Envoie dans l'ordre de création, une conversation après l'autre. S'arrête à la première panne réseau (inutile
   * d'insister), marque en échec les refus définitifs et continue. Un seul vidage à la fois.
   */
  envoyerTout(envoyeur: Envoyeur, classer: Classeur): Promise<void> {
    if (enVol) return enVol;
    enVol = (async () => {
      const aEnvoyer = (await charger()).filter((e) => e.etat === "en_attente").sort((a, b) => a.creeLe - b.creeLe);
      const bloquees = new Set<string>(); // une conversation en panne bloque ses messages suivants (l'ordre compte)
      for (const e of aEnvoyer) {
        if (bloquees.has(e.conversationId)) continue;
        try {
          await envoyeur(e);
          await outbox.retirer(e.clientMsgId);
        } catch (erreur) {
          const verdict = classer(erreur);
          e.tentatives += 1;
          if (verdict.reessayer) {
            bloquees.add(e.conversationId);
            await sauver();
            if (e.tentatives >= 1) break; // réseau coupé : on s'arrête, la reprise se fera au retour de la connexion
          } else {
            e.etat = "echec";
            e.codeErreur = verdict.code;
            await sauver();
          }
        }
      }
    })().finally(() => {
      enVol = null;
    });
    return enVol;
  },
};

/** Pour les tests. */
export function _reinitialiserOutbox(): void {
  file = null;
  enVol = null;
  ecouteurs.clear();
}
