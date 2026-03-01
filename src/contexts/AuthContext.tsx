/**
 * SPARK Auth Context
 * ─────────────────────────────────────────────────────────────────────────────
 * JWT token lifecycle: login → in-memory access token → silently refresh
 * before expiry → logout clears both tokens.
 *
 * Refresh token is persisted in sessionStorage so reloads don't force re-login.
 * Access token intentionally stays in memory only (XSS mitigation).
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from 'react';
import { tokenStore, apiPost } from '@/lib/api';

// ── Types ────────────────────────────────────────────────────────────────────
export interface SparkUser {
  username: string;
  role: 'admin' | 'operator' | 'viewer';
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user?: SparkUser;
}

interface AuthState {
  user: SparkUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  clearError: () => void;
}

// ── Context ──────────────────────────────────────────────────────────────────
const AuthContext = createContext<AuthState | null>(null);

const REFRESH_KEY = 'spark_rt';
const REFRESH_MARGIN_MS = 60_000; // refresh 60s before expiry

// ── Provider ─────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser]         = useState<SparkUser | null>(null);
  const [isLoading, setLoading] = useState(true); // true while we attempt silent restore
  const [error, setError]       = useState<string | null>(null);
  const refreshTimerRef         = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Schedule proactive refresh ─────────────────────────────────────────────
  const scheduleRefresh = useCallback((expiresInMs: number) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    const delay = Math.max(expiresInMs - REFRESH_MARGIN_MS, 5_000);
    refreshTimerRef.current = setTimeout(async () => {
      const rt = sessionStorage.getItem(REFRESH_KEY);
      if (!rt) return;
      try {
        const data = await apiPost<LoginResponse>('/api/auth/refresh', { refresh_token: rt });
        tokenStore.setAccess(data.access_token);
        if (data.refresh_token) {
          sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
          tokenStore.setRefresh(data.refresh_token);
        }
        scheduleRefresh((data.expires_in ?? 3600) * 1000);
      } catch {
        // silent fail — user will hit 401 and be redirected on next request
        setUser(null);
        tokenStore.clear();
        sessionStorage.removeItem(REFRESH_KEY);
      }
    }, delay);
  }, []);

  // ── Silent restore on mount (uses refresh token from sessionStorage) ────────
  useEffect(() => {
    const rt = sessionStorage.getItem(REFRESH_KEY);
    if (!rt) { setLoading(false); return; }

    tokenStore.setRefresh(rt);
    apiPost<LoginResponse>('/api/auth/refresh', { refresh_token: rt })
      .then(data => {
        tokenStore.setAccess(data.access_token);
        if (data.refresh_token) {
          sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
          tokenStore.setRefresh(data.refresh_token);
        }
        setUser(data.user ?? { username: 'operator', role: 'operator' });
        scheduleRefresh((data.expires_in ?? 3600) * 1000);
      })
      .catch(() => {
        tokenStore.clear();
        sessionStorage.removeItem(REFRESH_KEY);
      })
      .finally(() => setLoading(false));
  }, [scheduleRefresh]);

  // ── Cleanup timer ─────────────────────────────────────────────────────────
  useEffect(() => {
    return () => { if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current); };
  }, []);

  // ── Login ──────────────────────────────────────────────────────────────────
  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    setError(null);
    setLoading(true);
    try {
      const data = await apiPost<LoginResponse>('/api/auth/login', { username, password });
      tokenStore.setAccess(data.access_token);
      tokenStore.setRefresh(data.refresh_token);
      sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
      setUser(data.user ?? { username, role: 'operator' });
      scheduleRefresh((data.expires_in ?? 3600) * 1000);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
      return false;
    } finally {
      setLoading(false);
    }
  }, [scheduleRefresh]);

  // ── Logout ──────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    try {
      await apiPost('/api/auth/logout', {});
    } catch { /* best-effort */ }
    tokenStore.clear();
    sessionStorage.removeItem(REFRESH_KEY);
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    setUser(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      error,
      login,
      logout,
      clearError,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside <AuthProvider>');
  return ctx;
}
