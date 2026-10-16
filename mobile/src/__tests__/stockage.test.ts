import { _reinitialiserOutbox, outbox, type Classeur, type ElementFile } from "@/storage/outbox";
import { kv } from "@/storage/kv";
import AsyncStorage from "@react-native-async-storage/async-storage";

beforeEach(async () => {
  _reinitialiserOutbox();
  await AsyncStorage.clear();
});

const nouveau = (n: number, conv = "c1") => ({ clientMsgId: `id-${n}`, conversationId: conv, body: `message ${n}` });
const toujoursReessayer: Classeur = () => ({ reessayer: true });
const refusDefinitif: Classeur = () => ({ reessayer: false, code: "contact_detected" });

describe("kv", () => {
  it("lit, écrit, supprime ; un contenu corrompu est jeté", async () => {
    await kv.set("a", { x: 1 });
    expect(await kv.get("a")).toEqual({ x: 1 });
    await AsyncStorage.setItem("b", "{pas du json");
    expect(await kv.get("b")).toBeNull();
    expect(await AsyncStorage.getItem("b")).toBeNull();
    await kv.remove("a");
    expect(await kv.get("a")).toBeNull();
  });
});

describe("file d'envoi", () => {
  it("garde le client_msg_id fixé à la création et survit à un redémarrage", async () => {
    await outbox.ajouter(nouveau(1));
    _reinitialiserOutbox(); // simule un redémarrage : seule la persistance reste
    const l = await outbox.lister();
    expect(l).toHaveLength(1);
    expect(l[0]).toMatchObject({ clientMsgId: "id-1", etat: "en_attente", tentatives: 0 });
  });

  it("envoie dans l'ordre de création puis vide la file", async () => {
    await outbox.ajouter(nouveau(2), 2000);
    await outbox.ajouter(nouveau(1), 1000);
    const envoyes: string[] = [];
    await outbox.envoyerTout(async (e) => void envoyes.push(e.clientMsgId), toujoursReessayer);
    expect(envoyes).toEqual(["id-1", "id-2"]);
    expect(await outbox.lister()).toEqual([]);
  });

  it("panne réseau : s'arrête, garde le message en attente avec le MÊME client_msg_id", async () => {
    await outbox.ajouter(nouveau(1));
    await outbox.ajouter(nouveau(2));
    const appels: string[] = [];
    await outbox.envoyerTout(async (e) => { appels.push(e.clientMsgId); throw new Error("réseau"); }, toujoursReessayer);
    expect(appels).toEqual(["id-1"]); // inutile d'insister sur le suivant
    const reste = await outbox.lister();
    expect(reste.map((e) => [e.clientMsgId, e.etat])).toEqual([["id-1", "en_attente"], ["id-2", "en_attente"]]);
    expect(reste[0]?.tentatives).toBe(1);
  });

  it("refus définitif : marqué en échec avec son code, les suivants partent", async () => {
    await outbox.ajouter(nouveau(1));
    await outbox.ajouter(nouveau(2));
    const envoyes: string[] = [];
    await outbox.envoyerTout(async (e) => { if (e.clientMsgId === "id-1") throw new Error("422"); envoyes.push(e.clientMsgId); }, refusDefinitif);
    expect(envoyes).toEqual(["id-2"]);
    const l = await outbox.lister();
    expect(l).toHaveLength(1);
    expect(l[0]).toMatchObject({ clientMsgId: "id-1", etat: "echec", codeErreur: "contact_detected" });
  });

  it("une conversation en panne ne bloque pas les autres... jusqu'à la panne réseau (on s'arrête)", async () => {
    await outbox.ajouter(nouveau(1, "A"), 1);
    await outbox.ajouter(nouveau(2, "B"), 2);
    const appels: string[] = [];
    await outbox.envoyerTout(async (e) => { appels.push(e.clientMsgId); throw new Error("réseau"); }, toujoursReessayer);
    expect(appels).toHaveLength(1);
  });

  it("« Renvoyer » remet en attente et efface le code d'erreur", async () => {
    await outbox.ajouter(nouveau(1));
    await outbox.envoyerTout(async () => { throw new Error("x"); }, refusDefinitif);
    await outbox.relancer("id-1");
    expect((await outbox.lister())[0]).toMatchObject({ etat: "en_attente", codeErreur: undefined });
  });

  it("un seul vidage à la fois (pas de double envoi)", async () => {
    await outbox.ajouter(nouveau(1));
    let appels = 0;
    const lent = async () => { appels += 1; await new Promise((r) => setTimeout(r, 20)); };
    await Promise.all([outbox.envoyerTout(lent, toujoursReessayer), outbox.envoyerTout(lent, toujoursReessayer)]);
    expect(appels).toBe(1);
  });

  it("retirer, vider, abonnés et instantané", async () => {
    const seen: ElementFile[][] = [];
    const stop = outbox.abonner(() => seen.push(outbox.instantane()));
    await outbox.ajouter(nouveau(1));
    await outbox.ajouter(nouveau(2));
    expect(new Set(seen.map((s) => s)).size).toBe(seen.length); // une référence neuve à chaque changement
    await outbox.retirer("id-1");
    expect((await outbox.lister()).map((e) => e.clientMsgId)).toEqual(["id-2"]);
    await outbox.vider();
    expect(outbox.instantane()).toEqual([]);
    expect(await AsyncStorage.getItem("logeo.outbox")).toBeNull();
    stop();
  });
});
