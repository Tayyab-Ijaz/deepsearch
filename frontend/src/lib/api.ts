import { API_URL } from './config';
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from './tokens';
import type { AuthSession } from './types';

export class ApiError extends Error {
  constructor(message: string, public readonly status = 0, public readonly sessionExpired = false) {
    super(message);
    this.name = 'ApiError';
  }
}

type Options = { body?: unknown; auth?: boolean };

let onExpired: (() => void) | null = null;
let refreshing: Promise<void> | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onExpired = handler;
}

async function perform(method: string, path: string, body: unknown, auth: boolean): Promise<{ status: number; data: unknown }> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = getAccessToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(`${API_URL}/${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    let data: unknown = null;
    const text = await response.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
    return { status: response.status, data };
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('The request took too long. Please try again.');
    }
    throw new ApiError('Could not reach DeepSearch AI. Check your internet connection and try again.');
  } finally {
    clearTimeout(timer);
  }
}

function serverMessage(data: unknown, status: number): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === 'string' && detail) {
      if (/traceback|module not found|exception|stack trace|\.py:\d+|firebase_admin|sqlalchemy/i.test(detail)) {
        return status >= 500 ? 'DeepSearch AI is having trouble right now. Please try again later.' : 'We could not complete that request. Please check your details and try again.';
      }
      return detail;
    }
  }
  if (status === 429) return 'Too many requests. Please wait a moment.';
  if (status >= 500) return 'DeepSearch AI is having trouble right now. Please try again later.';
  return 'We could not complete that request. Please try again.';
}

async function renewSession(): Promise<void> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) throw new ApiError('Please sign in again.', 401, true);
    const { status, data } = await perform('POST', 'api/auth/refresh', { refresh_token: refresh }, false);
    if (status !== 200) throw new ApiError('Please sign in again.', 401, true);
    const session = data as AuthSession;
    await saveTokens(session.access_token, session.refresh_token);
  })().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function expire(): Promise<never> {
  await clearTokens();
  onExpired?.();
  throw new ApiError('Your session has ended. Please sign in again.', 401, true);
}

export async function request<T>(method: string, path: string, options: Options = {}): Promise<T> {
  const auth = options.auth ?? true;
  let result = await perform(method, path, options.body, auth);

  if (result.status === 401 && auth) {
    try {
      await renewSession();
    } catch {
      return expire();
    }
    result = await perform(method, path, options.body, auth);
    if (result.status === 401) return expire();
  }

  if (result.status < 200 || result.status >= 300) {
    throw new ApiError(serverMessage(result.data, result.status), result.status);
  }
  return result.data as T;
}

export const api = {
  get: <T,>(path: string) => request<T>('GET', path),
  post: <T,>(path: string, body?: unknown, auth = true) => request<T>('POST', path, { body, auth }),
  del: <T,>(path: string, body?: unknown) => request<T>('DELETE', path, { body }),
};

export function errorText(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return 'We could not complete that request. Please try again.';
}
