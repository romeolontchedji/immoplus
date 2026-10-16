/** Le client HTTP est chargé APRÈS la mise en place d'un faux `fetch` : openapi-fetch le capture à la création. */
import { ApiError, NetworkError } from "@/api/errors";
import { apiEvents } from "@/api/events";
import { _reinitialiser, accessToken, storeTokens } from "@/api/session";

type Reponse = { status: number; corps?: unknown; entetes?: Record<string, string> };
let journal: Request[] = [];
let scenario: (r: Request, n: number) => Reponse | Error = () => ({ status: 200, corps: {} });

function installer() {
  journal = [];
  global.fetch = jest.fn(async (entree: Request | string) => {
    const requete = entree instanceof Request ? entree : new Request(entree);
    journal.push(requete.clone());
    const r = scenario(requete, journal.length);
    if (r instanceof Error) throw r;
    return new Response(r.status === 204 ? null : JSON.stringify(r.corps ?? {}), { status: r.status, headers: { "Content-Type": "application/json", ...(r.entetes ?? {}) } });
  }) as unknown as typeof fetch;
}

let api: typeof import("@/api/client").api;
let unwrap: typeof import("@/api/client").unwrap;

beforeAll(() => {
  installer();
  ({ api, unwrap } = require("@/api/client"));
});
beforeEach(() => {
  installer();
  _reinitialiser();
  require("@/api/client"); // rebranche le renouveleur effacé par _reinitialiser
  jest.isolateModules(() => undefined);
});

async function brancherRenouveleurReel() {
  const { brancherRenouveleur } = require("@/api/session");
  brancherRenouveleur(async (refresh: string) => {
    const r = await fetch(new Request("http://localhost/v1/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: refresh }) }));
    return r.ok ? ((await r.json()) as { access: string; refresh: string; expires_in: number }) : null;
  });
}

describe("en-têtes", () => {
  it("version de l'application, installation, langue et jeton", async () => {
    await storeTokens({ access: "JETON", refresh: "R" });
    await unwrap(api.GET("/v1/app-config"));
    const h = journal[0]?.headers;
    expect(h?.get("X-App-Version")).toMatch(/^\d+\.\d+\.\d+$/);
    expect(h?.get("X-Installation-Id")).toMatch(/^[0-9a-f-]{36}$/);
    expect(h?.get("Accept-Language")).toBe("fr");
    expect(h?.get("Authorization")).toBe("Bearer JETON");
  });
  it("pas de jeton : pas d'en-tête Authorization", async () => {
    await unwrap(api.GET("/v1/app-config"));
    expect(journal[0]?.headers.get("Authorization")).toBeNull();
  });
});

describe("événements globaux", () => {
  it("426 → mise à jour obligatoire", async () => {
    scenario = () => ({ status: 426, corps: { error: { code: "upgrade_required", message: "x" } } });
    const f = jest.fn();
    apiEvents.on("upgrade_required", f);
    await expect(unwrap(api.GET("/v1/listings"))).rejects.toMatchObject({ code: "upgrade_required", status: 426 });
    expect(f).toHaveBeenCalled();
  });
  it("503 maintenance → écran de maintenance ; un autre 503 ne l'est pas", async () => {
    const f = jest.fn();
    apiEvents.on("maintenance", f);
    scenario = () => ({ status: 503, corps: { error: { code: "service_unavailable", message: "x" } } });
    await expect(unwrap(api.GET("/v1/listings"))).rejects.toBeInstanceOf(ApiError);
    expect(f).not.toHaveBeenCalled();
    scenario = () => ({ status: 503, corps: { error: { code: "maintenance", message: "Retour à 14 h." } } });
    await expect(unwrap(api.GET("/v1/listings"))).rejects.toBeInstanceOf(ApiError);
    expect(f).toHaveBeenCalledTimes(1);
  });
});

describe("renouvellement du jeton sur 401", () => {
  it("renouvelle une fois puis rejoue la requête avec le nouveau jeton", async () => {
    await storeTokens({ access: "vieux", refresh: "R1" });
    await brancherRenouveleurReel();
    scenario = (r) => {
      if (r.url.endsWith("/v1/auth/refresh")) return { status: 200, corps: { access: "neuf", refresh: "R2", expires_in: 900 } };
      return r.headers.get("Authorization") === "Bearer neuf" ? { status: 200, corps: { items: [], next_cursor: null } } : { status: 401, corps: { error: { code: "invalid_token", message: "x" } } };
    };
    const donnees = await unwrap(api.GET("/v1/listings"));
    expect(donnees).toEqual({ items: [], next_cursor: null });
    expect(accessToken()).toBe("neuf");
    expect(journal.map((r) => new URL(r.url).pathname)).toEqual(["/v1/listings", "/v1/auth/refresh", "/v1/listings"]);
  });
  it("refresh refusé : l'erreur 401 remonte, une seule tentative", async () => {
    await storeTokens({ access: "vieux", refresh: "R1" });
    await brancherRenouveleurReel();
    scenario = (r) => (r.url.endsWith("/v1/auth/refresh") ? { status: 401, corps: {} } : { status: 401, corps: { error: { code: "invalid_token", message: "x" } } });
    await expect(unwrap(api.GET("/v1/me"))).rejects.toMatchObject({ status: 401 });
    expect(journal.filter((r) => r.url.endsWith("/v1/auth/refresh"))).toHaveLength(1);
  });
  it("jamais de renouvellement pour la connexion elle-même", async () => {
    await storeTokens({ access: "A", refresh: "R" });
    scenario = () => ({ status: 401, corps: { error: { code: "invalid_credentials", message: "x" } } });
    await expect(unwrap(api.POST("/v1/auth/login", { body: { platform: "android", label: "t", phone: "+22997123456", password: "x" } }))).rejects.toMatchObject({ code: "invalid_credentials" });
    expect(journal).toHaveLength(1);
  });
});

describe("unwrap", () => {
  it("erreur métier → ApiError avec champs", async () => {
    scenario = () => ({ status: 422, corps: { error: { code: "validation_error", message: "Non.", fields: { body: ["Vide"] } } } });
    const e = await unwrap(api.GET("/v1/listings")).catch((x: unknown) => x);
    expect(e).toBeInstanceOf(ApiError);
    expect((e as ApiError).field("body")).toBe("Vide");
  });
  it("réseau coupé → NetworkError", async () => {
    scenario = () => new TypeError("Network request failed");
    await expect(unwrap(api.GET("/v1/listings"))).rejects.toBeInstanceOf(NetworkError);
  });
  it("204 sans corps → undefined", async () => {
    scenario = () => ({ status: 204 });
    await expect(unwrap(api.DELETE("/v1/notifications/{notification_id}/read" as never, {} as never))).resolves.toBeUndefined();
  });
});
