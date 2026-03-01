/**
 * SPARK API Client
 * ─────────────────────────────────────────────────────────────────────────────
 * Central fetch wrapper that:
 *  • Attaches Authorization: Bearer <token> from in-memory store
 *  • Retries once after auto-refreshing on 401
 *  • Exports typed helpers: apiGet, apiPost, apiDelete
 */

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

// ── Token store (in-memory — not localStorage, avoids XSS) ───────────────────
let _accessToken: string | null = null;
let _refreshToken: string | null = null;

export const tokenStore = {
  setAccess: (t: string) => { _accessToken = t; },
  setRefresh: (t: string) => { _refreshToken = t; },
  getAccess: () => _accessToken,
  getRefresh: () => _refreshToken,
  clear: () => { _accessToken = null; _refreshToken = null; },
};

// ── Internal refresh ─────────────────────────────────────────────────────────
async function doRefresh(): Promise<boolean> {
  if (!_refreshToken) return false;
  try {
    const res = await fetch(`${BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: _refreshToken }),
    });
    if (!res.ok) { tokenStore.clear(); return false; }
    const data = await res.json();
    _accessToken = data.access_token;
    if (data.refresh_token) _refreshToken = data.refresh_token;
    return true;
  } catch {
    tokenStore.clear();
    return false;
  }
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (_accessToken) headers.set('Authorization', `Bearer ${_accessToken}`);

  let res = await fetch(`${BASE}${path}`, { ...init, headers });

  // Auto-refresh on 401 and retry once
  if (res.status === 401 && _refreshToken) {
    const ok = await doRefresh();
    if (ok && _accessToken) {
      headers.set('Authorization', `Bearer ${_accessToken}`);
      res = await fetch(`${BASE}${path}`, { ...init, headers });
    }
  }

  return res;
}

// ── Typed helpers ─────────────────────────────────────────────────────────────
export async function apiGet<T>(path: string): Promise<T> {
  const res = await apiFetch(path, { method: 'GET' });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `POST ${path} → ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await apiFetch(path, { method: 'DELETE' });
  if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}
