import { analyser } from "@/realtime/events";
import { ClientTempsReel, delaiReconnexion, type EtatConnexion } from "@/realtime/client";

class FauxWebSocket {
  static instances: FauxWebSocket[] = [];
  onopen?: () => void;
  onmessage?: (m: { data: unknown }) => void;
  onclose?: (e: { code?: number }) => void;
  onerror?: () => void;
  envoyes: string[] = [];
  fermeAvec?: number;
  constructor(public url: string) {
    FauxWebSocket.instances.push(this);
  }
  send(t: string) {
    this.envoyes.push(t);
  }
  close(code?: number) {
    this.fermeAvec = code;
    this.onclose?.({ code });
  }
  ouvrir() {
    this.onopen?.();
  }
  recevoir(objet: unknown) {
    this.onmessage?.({ data: JSON.stringify(objet) });
  }
}

const attendre = (ms = 0) => new Promise((r) => setTimeout(r, ms));

function creer(extra: Partial<ConstructorParameters<typeof ClientTempsReel>[0]> = {}) {
  FauxWebSocket.instances = [];
  const evenements: unknown[] = [];
  const etats: EtatConnexion[] = [];
  const ouvertures: boolean[] = [];
  let n = 0;
  const client = new ClientTempsReel({
    url: "ws://hote/ws/v1/",
    ticket: async () => `ticket-${++n}`,
    surEvenement: (e) => evenements.push(e),
    surEtat: (e) => etats.push(e),
    surOuverture: (p) => ouvertures.push(p),
    WebSocketImpl: FauxWebSocket as unknown as typeof WebSocket,
    aleatoire: () => 0,
    ...extra,
  });
  return { client, evenements, etats, ouvertures };
}

describe("délai de reconnexion", () => {
  it("1 s, 2 s, 4 s… plafonné à 30 s, avec au plus 25 % d'aléa", () => {
    expect([0, 1, 2, 3, 4, 5, 6, 10].map((n) => delaiReconnexion(n, () => 0))).toEqual([1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000]);
    expect(delaiReconnexion(0, () => 1)).toBe(1250);
    expect(delaiReconnexion(9, () => 1)).toBe(37500);
  });
});

describe("analyse des événements", () => {
  it("accepte les types connus, ignore les autres et le non-JSON", () => {
    expect(analyser('{"type":"message.new","data":{"conversation_id":"c"}}')?.type).toBe("message.new");
    expect(analyser('{"type":"futur.inconnu","data":{}}')).toBeNull();
    expect(analyser("pas du json")).toBeNull();
    expect(analyser('{"data":{}}')).toBeNull();
  });
});

describe("client temps réel", () => {
  it("un ticket par connexion, dans l'URL ; rend les événements, pas les pong", async () => {
    const { client, evenements, etats, ouvertures } = creer();
    client.demarrer();
    await attendre();
    const ws = FauxWebSocket.instances[0] as FauxWebSocket;
    expect(ws.url).toBe("ws://hote/ws/v1/?ticket=ticket-1");
    ws.ouvrir();
    ws.recevoir({ type: "pong", data: {} });
    ws.recevoir({ type: "notification.new", data: { unread_count: 3 } });
    expect(evenements).toEqual([{ type: "notification.new", data: { unread_count: 3 } }]);
    expect(etats).toEqual(["connexion", "ouverte"]);
    expect(ouvertures).toEqual([true]);
    client.arreter();
  });

  it("annonce la conversation à l'écran, et la réannonce après une reconnexion", async () => {
    jest.useFakeTimers();
    const { client, ouvertures } = creer();
    client.definirFocus("conv-1");
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    const premiere = FauxWebSocket.instances[0] as FauxWebSocket;
    premiere.ouvrir();
    expect(JSON.parse(premiere.envoyes[0] as string)).toEqual({ type: "conversation.focus", data: { conversation_id: "conv-1" } });
    premiere.close(1006); // coupure
    await jest.advanceTimersByTimeAsync(1000); // 1re attente = 1 s
    const seconde = FauxWebSocket.instances[1] as FauxWebSocket;
    expect(seconde.url).toBe("ws://hote/ws/v1/?ticket=ticket-2"); // jamais le même ticket
    seconde.ouvrir();
    expect(JSON.parse(seconde.envoyes[0] as string).data.conversation_id).toBe("conv-1");
    expect(ouvertures).toEqual([true, false]);
    client.definirFocus(null);
    expect(JSON.parse(seconde.envoyes[1] as string).data.conversation_id).toBeNull();
    client.arreter();
    jest.useRealTimers();
  });

  it("attente croissante entre les échecs, remise à zéro après une connexion réussie", async () => {
    jest.useFakeTimers();
    const { client } = creer();
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    FauxWebSocket.instances[0]?.close(1006);
    await jest.advanceTimersByTimeAsync(999);
    expect(FauxWebSocket.instances).toHaveLength(1);
    await jest.advanceTimersByTimeAsync(1);
    expect(FauxWebSocket.instances).toHaveLength(2);
    FauxWebSocket.instances[1]?.close(1006); // 2e échec : 2 s
    await jest.advanceTimersByTimeAsync(1999);
    expect(FauxWebSocket.instances).toHaveLength(2);
    await jest.advanceTimersByTimeAsync(1);
    expect(FauxWebSocket.instances).toHaveLength(3);
    FauxWebSocket.instances[2]?.ouvrir(); // succès : le compteur repart de zéro
    FauxWebSocket.instances[2]?.close(1006);
    await jest.advanceTimersByTimeAsync(1000);
    expect(FauxWebSocket.instances).toHaveLength(4);
    client.arreter();
    jest.useRealTimers();
  });

  it("compte suspendu (4403) : état « refusée », aucune reconnexion", async () => {
    jest.useFakeTimers();
    const { client, etats } = creer();
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    FauxWebSocket.instances[0]?.close(4403);
    await jest.advanceTimersByTimeAsync(120_000);
    expect(FauxWebSocket.instances).toHaveLength(1);
    expect(etats.at(-1)).toBe("refusee");
    jest.useRealTimers();
  });

  it("trop d'événements (4429) : attente d'au moins une minute", async () => {
    jest.useFakeTimers();
    const { client } = creer();
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    FauxWebSocket.instances[0]?.close(4429);
    await jest.advanceTimersByTimeAsync(59_000);
    expect(FauxWebSocket.instances).toHaveLength(1);
    await jest.advanceTimersByTimeAsync(1_000);
    expect(FauxWebSocket.instances).toHaveLength(2);
    client.arreter();
    jest.useRealTimers();
  });

  it("ping régulier ; sans réponse, la connexion est fermée puis rétablie", async () => {
    jest.useFakeTimers();
    const { client } = creer({ intervallePingMs: 1000, delaiPongMs: 500 });
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    const ws = FauxWebSocket.instances[0] as FauxWebSocket;
    ws.ouvrir();
    await jest.advanceTimersByTimeAsync(1000);
    expect(ws.envoyes.map((e) => JSON.parse(e).type)).toContain("ping");
    await jest.advanceTimersByTimeAsync(500); // pas de pong
    expect(ws.fermeAvec).toBe(4000);
    await jest.advanceTimersByTimeAsync(1000);
    expect(FauxWebSocket.instances.length).toBeGreaterThanOrEqual(2);
    client.arreter();
    jest.useRealTimers();
  });

  it("un pong à temps garde la connexion", async () => {
    jest.useFakeTimers();
    const { client } = creer({ intervallePingMs: 1000, delaiPongMs: 500 });
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    const ws = FauxWebSocket.instances[0] as FauxWebSocket;
    ws.ouvrir();
    await jest.advanceTimersByTimeAsync(1000);
    ws.recevoir({ type: "pong", data: {} });
    await jest.advanceTimersByTimeAsync(1400); // le 2e ping part à 2000 ms ; son attente de pong expire à 2500 ms
    expect(ws.fermeAvec).toBeUndefined();
    client.arreter();
    jest.useRealTimers();
  });

  it("arrêt volontaire : ferme proprement et ne se reconnecte pas", async () => {
    jest.useFakeTimers();
    const { client, etats } = creer();
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    const ws = FauxWebSocket.instances[0] as FauxWebSocket;
    ws.ouvrir();
    client.arreter();
    expect(ws.fermeAvec).toBe(1000);
    await jest.advanceTimersByTimeAsync(60_000);
    expect(FauxWebSocket.instances).toHaveLength(1);
    expect(etats.at(-1)).toBe("arretee");
    jest.useRealTimers();
  });

  it("échec d'obtention du ticket : nouvelle tentative plus tard", async () => {
    jest.useFakeTimers();
    let essais = 0;
    const { client } = creer({ ticket: async () => { if (++essais === 1) throw new Error("401"); return "ok"; } });
    client.demarrer();
    await jest.advanceTimersByTimeAsync(0);
    expect(FauxWebSocket.instances).toHaveLength(0);
    await jest.advanceTimersByTimeAsync(1000);
    expect(FauxWebSocket.instances[0]?.url).toContain("ticket=ok");
    client.arreter();
    jest.useRealTimers();
  });
});
