import * as SecureStore from "expo-secure-store";
import { apiEvents } from "@/api/events";
import { _reinitialiser, accessToken, brancherRenouveleur, clearSession, hasRefreshToken, installationId, refreshTokens, storeTokens } from "@/api/session";

const magasin = (SecureStore as unknown as { __magasin: Map<string, string> }).__magasin;
beforeEach(() => {
  _reinitialiser();
  magasin.clear();
});

describe("session", () => {
  it("le jeton d'accès reste en mémoire, le jeton de rafraîchissement va au coffre", async () => {
    await storeTokens({ access: "A1", refresh: "R1" });
    expect(accessToken()).toBe("A1");
    expect(magasin.get("immoplus.refresh")).toBe("R1");
    expect([...magasin.values()]).not.toContain("A1");
    expect(await hasRefreshToken()).toBe(true);
    await clearSession();
    expect(accessToken()).toBeNull();
    expect(await hasRefreshToken()).toBe(false);
  });

  it("l'identifiant d'installation est créé une fois puis réutilisé", async () => {
    const a = await installationId();
    _reinitialiser(); // même appareil, nouveau processus
    expect(await installationId()).toBe(a);
  });

  it("renouvellement à vol unique : dix requêtes en 401 = un seul appel", async () => {
    await storeTokens({ access: "vieux", refresh: "R1" });
    const renouveleur = jest.fn(async () => { await new Promise((r) => setTimeout(r, 10)); return { access: "neuf", refresh: "R2", expires_in: 900 }; });
    brancherRenouveleur(renouveleur);
    const resultats = await Promise.all(Array.from({ length: 10 }, () => refreshTokens()));
    expect(resultats.every(Boolean)).toBe(true);
    expect(renouveleur).toHaveBeenCalledTimes(1);
    expect(accessToken()).toBe("neuf");
    expect(magasin.get("immoplus.refresh")).toBe("R2"); // rotation du jeton de rafraîchissement
  });

  it("refus du serveur : session effacée et interface prévenue", async () => {
    await storeTokens({ access: "A", refresh: "R" });
    brancherRenouveleur(async () => null);
    const prevenu = jest.fn();
    apiEvents.on("signed_out", prevenu);
    expect(await refreshTokens()).toBe(false);
    expect(prevenu).toHaveBeenCalledWith("session_expiree");
    expect(await hasRefreshToken()).toBe(false);
  });

  it("panne réseau : la session est conservée", async () => {
    await storeTokens({ access: "A", refresh: "R" });
    brancherRenouveleur(async () => { throw new Error("réseau"); });
    expect(await refreshTokens()).toBe(false);
    expect(await hasRefreshToken()).toBe(true);
  });

  it("sans jeton de rafraîchissement : faux, sans appel", async () => {
    const renouveleur = jest.fn();
    brancherRenouveleur(renouveleur);
    expect(await refreshTokens()).toBe(false);
    expect(renouveleur).not.toHaveBeenCalled();
  });
});
