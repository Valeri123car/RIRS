/** Osnovni naslov backend API; nastavi se v .env.local (NEXT_PUBLIC_API_URL). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8989";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ValidationIssue = { msg?: string };

/** Iz FastAPI odgovora o napaki naredi sporočilo za uporabnika. */
function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((issue: ValidationIssue) => (issue.msg ?? "").replace(/^Value error, /, ""))
      .filter(Boolean)
      .join(" ");
  }
  return fallback;
}

type RequestOptions = {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
};

/**
 * Zahteva na backend. Piškotki se pošljejo (credentials: "include"), da deluje osvežilni
 * žeton v HttpOnly piškotku. Vrne JSON (ali undefined pri 204) oziroma vrže ApiError.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.token) headers.Authorization = `Bearer ${options.token}`;

  const response = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: "include",
    signal: options.signal,
  });

  if (response.status === 204) return undefined as T;
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(body, `Zahteva ni uspela (${response.status}).`));
  }
  return body as T;
}

/** GET zahteva na backend, ki vrne JSON ali vrže ApiError. */
export async function apiGet<T>(path: string, init?: { signal?: AbortSignal }): Promise<T> {
  return apiRequest<T>(path, { signal: init?.signal });
}
