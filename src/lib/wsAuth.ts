import { tokenStore } from './api';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

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
