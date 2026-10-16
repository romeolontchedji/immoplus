import createClient, { type Middleware } from "openapi-fetch";
import { API_URL, APP_VERSION } from "@/config/env";
import type { paths } from "./genere/api";
import { ApiError, NetworkError, toApiError } from "./errors";
import { apiEvents } from "./events";
import { accessToken, brancherRenouveleur, hasRefreshToken, installationId, refreshTokens, type Jetons } from "./session";

/** Client typé : chemins, paramètres et réponses viennent du schéma OpenAPI (`npm run api:generer`). */
export const api = createClient<paths>({ baseUrl: API_URL });

const COPIES = new WeakMap<Request, Request>();
const SANS_RENOUVELLEMENT = ["/v1/auth/login", "/v1/auth/refresh", "/v1/auth/register", "/v1/auth/otp/", "/v1/auth/password/reset"];

const middleware: Middleware = {
  async onRequest({ request }) {
    COPIES.set(request, request.clone()); // pour rejouer la requête après un renouvellement de jeton
    request.headers.set("X-App-Version", APP_VERSION);
    request.headers.set("X-Installation-Id", await installationId());
    request.headers.set("Accept-Language", "fr");
    const jeton = accessToken();
    if (jeton) request.headers.set("Authorization", `Bearer ${jeton}`);
    return request;
  },
  async onResponse({ request, response }) {
    if (response.status === 426) apiEvents.emit("upgrade_required");
    if (response.status === 503) {
      const corps: unknown = await response.clone().json().catch(() => null);
      if ((corps as { error?: { code?: string } } | null)?.error?.code === "maintenance") apiEvents.emit("maintenance");
    }
    const url = new URL(request.url).pathname;
    if (response.status === 401 && !SANS_RENOUVELLEMENT.some((p) => url.startsWith(p)) && (await hasRefreshToken())) {
      const copie = COPIES.get(request);
      if (copie && (await refreshTokens())) {
        copie.headers.set("Authorization", `Bearer ${accessToken() ?? ""}`);
        return fetch(copie); // une seule relance : si elle échoue encore, l'erreur remonte
      }
    }
    return undefined;
  },
};
api.use(middleware);

/** Renouvellement des jetons (branché sur la session). `null` = refusé : la session est terminée. */
brancherRenouveleur(async (refresh_token): Promise<Jetons | null> => {
  const { data, response } = await api.POST("/v1/auth/refresh", { body: { refresh_token } });
  if (data) return data as Jetons;
  if (response.status === 401 || response.status === 403 || response.status === 400) return null;
  throw new NetworkError(response.status); // 5xx : on ne détruit pas la session pour une panne serveur
});

type Resultat<T> = { data?: T; error?: unknown; response: Response };

/** Extrait `data` ou lève `ApiError` / `NetworkError`. Tous les appels des hooks passent par là. */
export async function unwrap<T>(appel: Promise<Resultat<T>>): Promise<T> {
  let r: Resultat<T>;
  try {
    r = await appel;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new NetworkError(e);
  }
  if (r.response.ok) return (r.data as T) ?? (undefined as T); // 204 : pas de corps
  throw toApiError(r.response.status, r.error, r.response.headers);
}
