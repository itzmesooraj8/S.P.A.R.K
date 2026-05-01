import { tokenStore } from './api';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;

    const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padLength = normalized.length % 4;
    const padded = padLength === 0 ? normalized : `${normalized}${'='.repeat(4 - padLength)}`;
    const json = atob(padded);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function hasValidAccessToken(skewMs = 5000): boolean {
  const token = tokenStore.getAccess();
  if (!token) return false;

  const payload = decodeJwtPayload(token);
  const exp = typeof payload?.exp === 'number' ? payload.exp : null;
  if (!exp) return true;

  return Date.now() + skewMs < exp * 1000;
}

export function shouldReconnectAfterClose(closeCode: number): boolean {
  // 1008 is policy violation (missing/invalid token in our backend WS auth).
  if (closeCode === 1008) return false;
  return hasValidAccessToken();
}

export function buildAuthedWsUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  let url: URL;

  try {
    const base = new URL(API_BASE);
    const protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    url = new URL(normalizedPath, `${protocol}//${base.host}`);
  } catch {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const port = import.meta.env.VITE_BACKEND_PORT ?? '8000';
    url = new URL(`${protocol}//${window.location.hostname}:${port}${normalizedPath}`);
  }

  const accessToken = tokenStore.getAccess();
  if (accessToken) {
    url.searchParams.set('token', accessToken);
  }

  return url.toString();
}
