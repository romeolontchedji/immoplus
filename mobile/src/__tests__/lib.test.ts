import { dateCourte, distance, fcfa, heure, jourRelatif } from "@/lib/format";
import { chiffres, formaterLocal, versE164 } from "@/lib/phone";
import { estInferieure } from "@/lib/version";
import { appliquerModeration, composerLignes, fusionner, type Message } from "@/lib/messages";

describe("format", () => {
  it("montants en FCFA avec espace fine", () => {
    expect(fcfa(25000)).toBe("25\u202F000 FCFA");
    expect(fcfa(1500000)).toBe("1\u202F500\u202F000 FCFA");
    expect(fcfa(900)).toBe("900 FCFA");
  });
  it("distances", () => {
    expect(distance(450)).toBe("450 m");
    expect(distance(1500)).toBe("1,5 km");
  });
  it("jours relatifs", () => {
    const maintenant = new Date(2026, 9, 10, 15, 0);
    expect(jourRelatif(new Date(2026, 9, 10, 8, 0).toISOString(), maintenant)).toBe("Aujourd'hui");
    expect(jourRelatif(new Date(2026, 9, 9, 23, 0).toISOString(), maintenant)).toBe("Hier");
    expect(jourRelatif(new Date(2026, 8, 1, 10, 0).toISOString(), maintenant)).toBe("1 sept. 2026");
  });
  it("heure et date courte", () => {
    const iso = new Date(2026, 0, 5, 9, 7).toISOString();
    expect(heure(iso)).toBe("09:07");
    expect(dateCourte(iso)).toBe("5 janv. 2026");
  });
});

describe("téléphone du Bénin", () => {
  it.each([
    ["97 12 34 56", "+22997123456"],
    ["0197123456", "+2290197123456"],
    ["+229 97 12 34 56", "+22997123456"],
    ["0022997123456", "+22997123456"],
  ])("%s → %s", (saisie, attendu) => expect(versE164(saisie)).toBe(attendu));
  it.each(["", "123", "12345678901234", "abcdefgh"])("refuse « %s »", (s) => expect(versE164(s)).toBeNull());
  it("groupe par deux", () => {
    expect(formaterLocal("97123456")).toBe("97 12 34 56");
    expect(chiffres("97 12-34.56")).toBe("97123456");
  });
});

describe("comparaison de versions", () => {
  it.each([
    ["1.0.0", "1.0.0", false],
    ["0.9.9", "1.0.0", true],
    ["1.9.0", "1.10.0", true], // numérique, pas alphabétique
    ["1.10.0", "1.9.0", false],
    ["2", "1.99.99", false],
    ["1.0", "1.0.1", true],
    ["n'importe quoi", "1.0.0", false], // illisible : jamais bloquant
    ["1.0.0", "", false],
  ])("%s < %s : %s", (a, b, attendu) => expect(estInferieure(a, b)).toBe(attendu));
});

const msg = (seq: number, extra: Partial<Message> = {}): Message => ({
  id: `m${seq}`, seq, sender_id: "u1", client_msg_id: `c${seq}`, kind: "text", body: `msg ${seq}`, moderation_status: "visible", flag_reason: null, created_at: "2026-10-10T10:00:00Z", ...extra,
});

describe("fusion de messages", () => {
  it("sans doublon, dans l'ordre de seq", () => {
    expect(fusionner([msg(2), msg(1)], [msg(3), msg(2)]).map((m) => m.seq)).toEqual([1, 2, 3]);
  });
  it("même client_msg_id d'un même expéditeur = un seul message (réponse HTTP + événement temps réel)", () => {
    expect(fusionner([msg(1)], [msg(1, { id: "autre" })])).toHaveLength(1);
  });
  it("le plus récent gagne (message modéré)", () => {
    expect(fusionner([msg(1)], [msg(1, { moderation_status: "deleted" })])[0]?.moderation_status).toBe("deleted");
  });
  it("modération appliquée au bon message", () => {
    const r = appliquerModeration([msg(1), msg(2)], "m2", "masked");
    expect(r.map((m) => m.moderation_status)).toEqual(["visible", "masked"]);
  });
  it("lignes : le message local confirmé par le serveur disparaît de la file", () => {
    const file = [
      { clientMsgId: "c1", body: "msg 1", etat: "en_attente" as const, creeLe: 1 },
      { clientMsgId: "cX", body: "pas encore parti", etat: "en_attente" as const, creeLe: 2 },
    ];
    const lignes = composerLignes([msg(1)], file, "u1", 1);
    expect(lignes.map((l) => (l.type === "serveur" ? "s" : "l"))).toEqual(["s", "l"]);
    expect(lignes[0]).toMatchObject({ lu: true });
  });
  it("« lu » seulement pour mes messages jusqu'à la lecture de l'autre", () => {
    const l = composerLignes([msg(1), msg(2, { sender_id: "u2" }), msg(3)], [], "u1", 2);
    expect(l.map((x) => (x.type === "serveur" ? x.lu : null))).toEqual([true, false, false]);
  });
});
