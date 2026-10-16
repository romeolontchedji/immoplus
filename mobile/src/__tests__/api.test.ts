import { ApiError, NetworkError, isRetryable, toApiError } from "@/api/errors";
import { apiEvents } from "@/api/events";
import { messageErreur } from "@/i18n/fr";

describe("erreurs de l'API", () => {
  it("lit le corps d'erreur standard", () => {
    const e = toApiError(422, { error: { code: "contact_detected", message: "Non.", fields: { body: ["Motif : telephone"] }, request_id: "r1" } });
    expect(e).toBeInstanceOf(ApiError);
    expect([e.status, e.code, e.requestId, e.field("body")]).toEqual([422, "contact_detected", "r1", "Motif : telephone"]);
  });
  it("corps inattendu : code http_<statut>, message générique", () => {
    const e = toApiError(502, "<html>");
    expect([e.code, e.status]).toEqual(["http_502", 502]);
    expect(e.message).toBe("Une erreur est survenue.");
  });
  it("Retry-After", () => {
    expect(toApiError(429, {}, { get: () => "60" }).retryAfterS).toBe(60);
    expect(toApiError(429, {}, { get: () => null }).retryAfterS).toBeUndefined();
  });
  it("réessayable : réseau, 429, 5xx ; pas les erreurs métier", () => {
    expect(isRetryable(new NetworkError())).toBe(true);
    expect(isRetryable(toApiError(429, {}))).toBe(true);
    expect(isRetryable(toApiError(503, {}))).toBe(true);
    expect(isRetryable(toApiError(422, {}))).toBe(false);
    expect(isRetryable(toApiError(401, {}))).toBe(false);
    expect(isRetryable(new Error("autre"))).toBe(false);
  });
  it("message pour l'utilisateur : par code, puis message du serveur, puis générique", () => {
    expect(messageErreur("invalid_credentials")).toBe("Numéro ou mot de passe incorrect.");
    expect(messageErreur("code_inconnu", "Texte du serveur")).toBe("Texte du serveur");
    expect(messageErreur(undefined)).toBe("Une erreur est survenue.");
  });
});

describe("événements globaux", () => {
  it("abonnement et désabonnement", () => {
    const f = jest.fn();
    const stop = apiEvents.on("maintenance", f);
    apiEvents.emit("maintenance");
    stop();
    apiEvents.emit("maintenance");
    expect(f).toHaveBeenCalledTimes(1);
  });
});
