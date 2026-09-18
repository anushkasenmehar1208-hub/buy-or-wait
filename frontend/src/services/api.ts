import type { ApiErrorShape } from '../types';

export const API_BASE_URL =
  (import.meta.env?.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

const TOKEN_KEY = 'bow_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    // Let the browser set multipart FormData boundaries; JSON otherwise.
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, 'NetworkError', 'Cannot reach the server. Is the backend running?');
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    // Expired/invalid session: drop the token and send the user to sign-in.
    // Sign-in/up failures are handled by their pages, so exclude those paths.
    if (response.status === 401 && token && !path.startsWith('/api/auth/')) {
      setToken(null);
      if (!window.location.pathname.startsWith('/signin')) {
        window.location.assign('/signin?expired=1');
      }
    }
    const err = (body as ApiErrorShape | null)?.error;
    throw new ApiError(
      response.status,
      err?.code ?? 'UnknownError',
      err?.message ?? `Request failed (${response.status})`,
    );
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: encodeBody(data) }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: 'PUT', body: encodeBody(data) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

/** JSON-encode plain objects; pass FormData through untouched (multipart). */
function encodeBody(data: unknown): BodyInit | undefined {
  if (data === undefined) return undefined;
  return data instanceof FormData ? data : JSON.stringify(data);
}
