/**
 * useConfigStatus
 * ─────────────────────────────────────────────────────────────────────────────
 * Polls GET /api/config/status every 30 s and exposes provider health data to
 * any consumer. Also syncs into useMonitorStore.providerHealth for globe panel.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';

export interface ProviderStatus {
  configured: boolean;
  available: boolean;
  model?: string;
  error?: string;
}

export interface ConfigStatus {
  providers: Record<string, ProviderStatus>;
  degraded_providers: string[];
  degraded_mode: boolean;
  jwt_secret_from_env: boolean;
}

export function useConfigStatus() {
  return useQuery<ConfigStatus>({
    queryKey: ['config-status'],
    queryFn: () => apiGet<ConfigStatus>('/api/config/status'),
    refetchInterval: 30_000,
    staleTime: 25_000,
    // Don't throw — show degraded UI gracefully
    retry: 2,
  });
}

// ── Color helpers for badge rendering ────────────────────────────────────────
export function providerStatusColor(p: ProviderStatus | undefined): string {
  if (!p) return '#ffffff30';
  if (p.available) return '#30d158';         // green = OK
  if (p.configured) return '#ff9f0a';        // amber = configured but unavailable
  return '#ff2d55';                          // red = not configured
}

export function providerStatusLabel(p: ProviderStatus | undefined): string {
  if (!p) return 'UNKNOWN';
  if (p.available) return 'OK';
  if (p.configured) return 'DEGRADED';
  return 'NO KEY';
}
