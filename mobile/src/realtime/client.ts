import { analyser, FERMETURE, type EvenementServeur } from "./events";

export type EtatConnexion = "arretee" | "connexion" | "ouverte" | "attente" | "refusee";

/** Attente avant la nième reconnexion : 1 s, 2 s, 4 s… plafonnée à 30 s, avec 0 à 25 % d'aléa (évite les reconnexions en rafale). */
export function delaiReconnexion(tentative: number, aleatoire: () => number = Math.random): number {
  const base = Math.min(1000 * 2 ** Math.max(0, tentative), 30_000);
  return Math.round(base * (1 + aleatoire() * 0.25));
}

type Options = {
  url: string;
  /** Obtient un ticket à usage unique (POST /v1/ws-ticket, valable 30 s). Un ticket par connexion, jamais réutilisé. */
  ticket: () => Promise<string>;
  surEvenement: (e: EvenementServeur) => void;
  surEtat?: (e: EtatConnexion) => void;
  /** Appelé à chaque (re)connexion réussie : l'appelant rattrape ce qu'il a manqué (`after_seq`, compteurs). */
  surOuverture?: (premiere: boolean) => void;
  WebSocketImpl?: typeof WebSocket;
  aleatoire?: () => number;
  intervallePingMs?: number;
  delaiPongMs?: number;
};

/**
 * Connexion temps réel. Le WebSocket ne sert qu'à **recevoir** (l'envoi se fait en HTTP, idempotent) et à annoncer
 * la conversation ouverte à l'écran (`conversation.focus`), ce qui supprime le push pour cet appareil.
 * Reconnexion automatique avec attente croissante ; arrêt définitif si le compte est suspendu (4403).
 */
export class ClientTempsReel {
  private ws: WebSocket | null = null;
  private etat: EtatConnexion = "arretee";
  private tentative = 0;
  private minuteurReconnexion: ReturnType<typeof setTimeout> | null = null;
  private minuteurPing: ReturnType<typeof setInterval> | null = null;
  private minuteurPong: ReturnType<typeof setTimeout> | null = null;
  private focus: string | null = null;
  private dejaOuverte = false;
  private actif = false;

  constructor(private readonly o: Options) {}

  get statut(): EtatConnexion {
    return this.etat;
  }

  demarrer(): void {
    if (this.actif) return;
    this.actif = true;
    this.tentative = 0;
    void this.connecter();
  }

  arreter(): void {
    this.actif = false;
    this.nettoyer();
    this.ws?.close(1000);
    this.ws = null;
    this.changer("arretee");
  }

  /** Conversation actuellement affichée (ou `null`). Mémorisée : renvoyée après chaque reconnexion. */
  definirFocus(conversationId: string | null): void {
    this.focus = conversationId;
    this.envoyerFocus();
  }

  private changer(e: EtatConnexion): void {
    this.etat = e;
    this.o.surEtat?.(e);
  }

  private async connecter(): Promise<void> {
    if (!this.actif) return;
    this.changer("connexion");
    let ticket: string;
    try {
      ticket = await this.o.ticket();
    } catch {
      return this.planifier();
    }
    if (!this.actif) return;
    const Impl = this.o.WebSocketImpl ?? WebSocket;
    const ws = new Impl(`${this.o.url}?ticket=${encodeURIComponent(ticket)}`);
    this.ws = ws;
    ws.onopen = () => {
      this.tentative = 0;
      this.changer("ouverte");
      this.envoyerFocus();
      this.demarrerPing();
      this.o.surOuverture?.(!this.dejaOuverte);
      this.dejaOuverte = true;
    };
    ws.onmessage = (m: { data: unknown }) => {
      this.armerPong(false);
      const e = typeof m.data === "string" ? analyser(m.data) : null;
      if (e && e.type !== "pong") this.o.surEvenement(e);
    };
    ws.onerror = () => undefined; // le détail arrive par onclose
    ws.onclose = (ev: { code?: number }) => {
      this.nettoyer();
      if (this.ws !== ws) return; // une connexion plus récente a pris le relais
      this.ws = null;
      if (!this.actif) return;
      if (ev.code === FERMETURE.compteSuspendu) {
        this.actif = false;
        return this.changer("refusee"); // inutile de réessayer : le compte ne peut pas écouter
      }
      this.planifier(ev.code === FERMETURE.tropDEvenements ? 60_000 : undefined);
    };
  }

  private planifier(minimum?: number): void {
    this.changer("attente");
    const delai = Math.max(minimum ?? 0, delaiReconnexion(this.tentative, this.o.aleatoire));
    this.tentative += 1;
    this.minuteurReconnexion = setTimeout(() => void this.connecter(), delai);
  }

  private envoyer(objet: unknown): void {
    if (this.ws && this.etat === "ouverte") this.ws.send(JSON.stringify(objet));
  }

  private envoyerFocus(): void {
    this.envoyer({ type: "conversation.focus", data: { conversation_id: this.focus } });
  }

  /** `ping` toutes les 25 s (le serveur ferme après 60 s de silence) ; sans réponse en 10 s, la connexion est considérée morte. */
  private demarrerPing(): void {
    this.minuteurPing = setInterval(() => {
      this.envoyer({ type: "ping" });
      this.armerPong(true);
    }, this.o.intervallePingMs ?? 25_000);
  }

  private armerPong(armer: boolean): void {
    if (this.minuteurPong) clearTimeout(this.minuteurPong);
    this.minuteurPong = armer
      ? setTimeout(() => this.ws?.close(4000), this.o.delaiPongMs ?? 10_000) // onclose déclenche la reconnexion
      : null;
  }

  private nettoyer(): void {
    if (this.minuteurReconnexion) clearTimeout(this.minuteurReconnexion);
    if (this.minuteurPing) clearInterval(this.minuteurPing);
    if (this.minuteurPong) clearTimeout(this.minuteurPong);
    this.minuteurReconnexion = this.minuteurPing = this.minuteurPong = null;
  }
}
