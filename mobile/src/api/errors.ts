/** Corps d'erreur de l'API : `{ "error": { code, message, fields?, request_id } }` (docs/api/README.md). */
export type CorpsErreur = {
  error: { code: string; message: string; fields?: Record<string, string[]>; request_id?: string };
};

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fields: Record<string, string[]>;
  readonly requestId?: string;
  readonly retryAfterS?: number;

  constructor(status: number, code: string, message: string, fields: Record<string, string[]> = {}, requestId?: string, retryAfterS?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.requestId = requestId;
    this.retryAfterS = retryAfterS;
  }

  /** Premier message d'erreur d'un champ de formulaire, s'il y en a un. */
  field(nom: string): string | undefined {
    return this.fields[nom]?.[0];
  }
}

/** Erreur réseau : pas de réponse du serveur (hors ligne, délai dépassé). À distinguer d'une erreur métier. */
export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super("Pas de connexion au serveur.");
    this.name = "NetworkError";
    this.cause = cause;
  }
}

export function toApiError(status: number, corps: unknown, entetes?: { get(nom: string): string | null }): ApiError {
  const e = (corps as Partial<CorpsErreur> | null)?.error;
  const retry = Number(entetes?.get("Retry-After"));
  return new ApiError(
    status,
    typeof e?.code === "string" ? e.code : `http_${status}`,
    typeof e?.message === "string" ? e.message : "Une erreur est survenue.",
    e?.fields ?? {},
    e?.request_id,
    Number.isFinite(retry) && retry > 0 ? retry : undefined,
  );
}

export const isApiError = (e: unknown): e is ApiError => e instanceof ApiError;
export const isNetworkError = (e: unknown): e is NetworkError => e instanceof NetworkError;

/** Une nouvelle tentative peut réussir (réseau, 429, 5xx) ; une erreur métier (4xx) ne changera pas en réessayant. */
export function isRetryable(e: unknown): boolean {
  if (isNetworkError(e)) return true;
  return isApiError(e) && (e.status === 429 || e.status >= 500);
}
