/** Osnovni naslov backend API; nastavi se v .env.local (NEXT_PUBLIC_API_URL). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** GET zahteva na backend, ki vrne JSON ali vrže ApiError. */
export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    throw new ApiError(response.status, `Zahteva ${path} ni uspela (${response.status})`);
  }
  return (await response.json()) as T;
}
