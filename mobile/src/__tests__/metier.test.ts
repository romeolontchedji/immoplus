import { QueryClient } from "@tanstack/react-query";
import { destination } from "@/features/notifications/routage";
import { FILTRES_VIDES, nombreDeFiltres, versParametres } from "@/features/listings/filtres";
import { CHAMPS_CREATION, champsManquants, type Brouillon } from "@/features/pro/brouillon";
import { qk } from "@/api/keys";
import { appliquerEvenement } from "@/realtime/cache";
import { queryClient } from "@/state/queryClient";
import type { HistoriqueLocal, Message } from "@/lib/messages";

jest.mock("@react-native-community/netinfo", () => require("@react-native-community/netinfo/jest/netinfo-mock.js"));

describe("routage des notifications", () => {
  it.each([
    ["message.received", { conversation_id: "c1" }, "client", { pathname: "/conversation/[id]", params: { id: "c1" } }],
    ["message.unanswered_reminder", { conversation_id: "c2" }, "gerant", { pathname: "/conversation/[id]", params: { id: "c2" } }],
    ["alert.match", { slug: "chambre-abc", listing_id: "L" }, "client", { pathname: "/annonces/[ident]", params: { ident: "chambre-abc" } }],
    ["favorite.unavailable", { slug: "x" }, "client", { pathname: "/annonces/[ident]", params: { ident: "x" } }],
    ["listing.hidden", { listing_id: "L1" }, "gerant", { pathname: "/pro/annonce/[id]", params: { id: "L1" } }],
    ["listing.media_failed", { listing_id: "L2" }, "gerant", { pathname: "/pro/annonce/[id]", params: { id: "L2" } }],
    ["listing.hidden", { listing_id: "L1" }, "client", "/notifications"], // un locataire n'a pas d'espace annonce
    ["account.sanction", {}, "client", "/notifications"],
    ["message.received", {}, "client", "/notifications"], // données incomplètes : jamais de route cassée
    [undefined, undefined, null, "/notifications"],
    ["type.futur", { x: 1 }, "gerant", "/notifications"],
  ])("%s (%j, %s)", (kind, data, role, attendu) => {
    expect(destination(kind, data as Record<string, unknown>, role as "client" | "gerant" | null)).toEqual(attendu);
  });
});

describe("filtres de recherche", () => {
  it("omet les valeurs vides, joint les listes par des virgules", () => {
    expect(versParametres({ ...FILTRES_VIDES, q: "  studio ", district: ["banikanni", "titirou"], type: ["studio"], rent_max: 25000, bathroom: true }, "CUR")).toEqual({
      q: "studio", district: "banikanni,titirou", type: "studio", rent_max: 25000, bathroom: true, fenced: undefined, max_distance_m: undefined, sort: "recent", cursor: "CUR",
    });
    const vide = versParametres(FILTRES_VIDES);
    expect(Object.values(vide).filter((v) => v !== undefined)).toEqual(["recent"]);
  });
  it("compte les filtres actifs (hors recherche texte et tri)", () => {
    expect(nombreDeFiltres(FILTRES_VIDES)).toBe(0);
    expect(nombreDeFiltres({ ...FILTRES_VIDES, q: "x", sort: "distance", district: ["a"], rent_max: 1, fenced: true })).toBe(3);
  });
});

describe("brouillon d'annonce", () => {
  const complet: Brouillon = {
    title: "Chambre", room_type: "single", rent_amount: 20000, deposit_months: 2, advance_months: 1, available_from: "2026-11-01", district: "d",
    landmark_text: "près du marché", address_private: "Rue 12", latitude: "9.34", longitude: "2.63", has_private_bathroom: false, is_fenced: true, water_source: "running", electricity_meter: "individual",
  };
  it("rien ne manque quand tout est saisi", () => expect(champsManquants(complet)).toEqual([]));
  it("fausse valeur booléenne ≠ valeur absente", () => expect(champsManquants({ ...complet, is_fenced: false })).toEqual([]));
  it("liste précisément ce qui manque, y compris les chaînes vides", () => {
    expect(champsManquants({ ...complet, title: "", rent_amount: undefined })).toEqual(["title", "rent_amount"]);
    expect(champsManquants({})).toHaveLength(CHAMPS_CREATION.length);
  });
});

describe("événements temps réel → cache", () => {
  const message = (seq: number, extra: Partial<Message> = {}): Message => ({
    id: `m${seq}`, seq, sender_id: "autre", client_msg_id: `c${seq}`, kind: "text", body: `msg ${seq}`, moderation_status: "visible", flag_reason: null, created_at: "2026-10-10T10:00:00Z", ...extra,
  });
  beforeEach(() => queryClient.clear());

  it("message.new s'ajoute à l'historique ouvert, sans doublon, et fait avancer dernierSeq", () => {
    queryClient.setQueryData<HistoriqueLocal>(qk.messages("c"), { items: [message(1)], plusAnciens: false, dernierSeq: 1 });
    appliquerEvenement({ type: "message.new", data: { conversation_id: "c", message: message(2) } });
    appliquerEvenement({ type: "message.new", data: { conversation_id: "c", message: message(2) } }); // rejoué
    const h = queryClient.getQueryData<HistoriqueLocal>(qk.messages("c"));
    expect(h?.items.map((m) => m.seq)).toEqual([1, 2]);
    expect(h?.dernierSeq).toBe(2);
  });
  it("message.new sans historique ouvert : rien à fusionner (la liste sera relue)", () => {
    appliquerEvenement({ type: "message.new", data: { conversation_id: "inconnue", message: message(1) } });
    expect(queryClient.getQueryData(qk.messages("inconnue"))).toBeUndefined();
  });
  it("message.moderated change l'état du bon message", () => {
    queryClient.setQueryData<HistoriqueLocal>(qk.messages("c"), { items: [message(1), message(2)], plusAnciens: false, dernierSeq: 2 });
    appliquerEvenement({ type: "message.moderated", data: { conversation_id: "c", message_id: "m2", seq: 2, moderation_status: "deleted" } });
    expect(queryClient.getQueryData<HistoriqueLocal>(qk.messages("c"))?.items.map((m) => m.moderation_status)).toEqual(["visible", "deleted"]);
  });
  it("notification.new met à jour la pastille immédiatement", () => {
    appliquerEvenement({ type: "notification.new", data: { unread_count: 7, notification: {} as never } });
    expect(queryClient.getQueryData(qk.nonLues)).toEqual({ unread_count: 7 });
  });
  it("conversation.read invalide la conversation et la liste", () => {
    const espion = jest.spyOn(queryClient, "invalidateQueries");
    appliquerEvenement({ type: "conversation.read", data: { conversation_id: "c", by: "u", up_to_seq: 3 } });
    const cles = espion.mock.calls.map((c) => JSON.stringify((c[0] as { queryKey: unknown }).queryKey));
    expect(cles).toEqual([JSON.stringify(qk.conversation("c")), JSON.stringify(qk.conversations)]);
    espion.mockRestore();
  });
  it("un type inconnu ou d'erreur ne casse rien", () => {
    expect(() => appliquerEvenement({ type: "error", data: { code: 4429 } })).not.toThrow();
    expect(() => appliquerEvenement({ type: "pong", data: {} })).not.toThrow();
  });
  it("(contrôle) un QueryClient neuf est bien isolé", () => expect(new QueryClient().getQueryCache().getAll()).toHaveLength(0));
});
