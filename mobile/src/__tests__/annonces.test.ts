import { annonces, annoncerNotification } from "@/features/notifications/annonces";
import { definirFocusActuel } from "@/realtime/focus";

describe("bannière interne (plan v2, N5)", () => {
  afterEach(() => {
    annonces.changer(null);
    definirFocusActuel(null);
  });

  it("annonce une notification reçue application ouverte", () => {
    annoncerNotification({ title: "Koffi · Studio", body: "Bonjour", kind: "message.received", data: { conversation_id: "c1" } });
    expect(annonces.lire()).toEqual({ titre: "Koffi · Studio", corps: "Bonjour", kind: "message.received", data: { conversation_id: "c1" } });
  });

  it("se tait pour la conversation déjà à l'écran", () => {
    definirFocusActuel("c1");
    annoncerNotification({ title: "Koffi", body: "Bonjour", kind: "message.received", data: { conversation_id: "c1" } });
    expect(annonces.lire()).toBeNull();
  });
});
