export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const BASE = "/api/v1";

interface Envelope<T> {
  data: T | null;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
}

/** Absolute URL for browser-native GETs (download links, EventSource). */
export function apiUrl(path: string): string {
  return `${BASE}${path}`;
}

/** Unwrap the {data,error} envelope; any non-JSON body surfaces as an ApiError. */
async function unwrap<T>(res: Response): Promise<T> {
  let body: Envelope<T>;
  try {
    body = (await res.json()) as Envelope<T>;
  } catch {
    throw new ApiError(
      "request_failed",
      `${res.status} ${res.statusText}`.trim(),
    );
  }
  if (body.error)
    throw new ApiError(
      body.error.code,
      body.error.message,
      body.error.details ?? {},
    );
  return body.data as T;
}

/** JSON endpoints — unwraps the {data,error} envelope, throws ApiError on error. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  return unwrap<T>(res);
}

/** Non-enveloped text endpoints (artifact preview). */
export async function requestText(path: string): Promise<string> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) {
    try {
      const body = (await res.json()) as Envelope<unknown>;
      if (body.error) {
        throw new ApiError(
          body.error.code,
          body.error.message,
          body.error.details ?? {},
        );
      }
    } catch (err) {
      if (err instanceof ApiError) throw err;
    }
    throw new ApiError("request_failed", `GET ${path} → ${res.status}`);
  }
  return res.text();
}

/** Multipart upload (recordings) — response IS enveloped. */
export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(apiUrl(path), { method: "POST", body: form });
  return unwrap<T>(res);
}
