import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API = 'http://localhost:8000';

export interface Plugin {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  status: 'active' | 'inactive' | 'error' | 'loading';
  enabled: boolean;
  auto_start: boolean;
  dependencies: string[];
  author: string;
  tags: string[];
  uptime: number;
  error_count: number;
  last_error: string | null;
  loaded_at: string | null;
}

export interface PluginStats {
  total: number;
  active: number;
  inactive: number;
  error: number;
  categories: Record<string, number>;
}

export function usePlugins() {
  const qc = useQueryClient();

  const { data: plugins = [], isLoading, error } = useQuery<Plugin[]>({
    queryKey: ['plugins'],
    queryFn: async () => {
      const res = await fetch(`${API}/api/plugins`);
      if (!res.ok) throw new Error('Failed to fetch plugins');
      const data = await res.json();
      return data.plugins ?? [];
    },
    refetchInterval: 5000,
    retry: 2,
  });

  const { data: stats } = useQuery<PluginStats>({
    queryKey: ['plugins-stats'],
    queryFn: async () => {
      const res = await fetch(`${API}/api/plugins/stats`);
      if (!res.ok) throw new Error('Failed to fetch plugin stats');
      return res.json();
    },
    refetchInterval: 5000,
    retry: 2,
  });

  const enableMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${API}/api/plugins/${id}/enable`, { method: 'POST' });
      if (!res.ok) throw new Error('Enable failed');
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plugins'] }),
  });

  const disableMutation = useMutation({
    mutationFn: async (id: string) => {
      const res = await fetch(`${API}/api/plugins/${id}/disable`, { method: 'POST' });
      if (!res.ok) throw new Error('Disable failed');
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plugins'] }),
  });

  const reloadMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API}/api/plugins/reload`, { method: 'POST' });
      if (!res.ok) throw new Error('Reload failed');
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plugins'] }),
  });

  return {
    plugins,
    stats,
    isLoading,
    error,
    enablePlugin: (id: string) => enableMutation.mutate(id),
    disablePlugin: (id: string) => disableMutation.mutate(id),
    reloadAll: () => reloadMutation.mutate(),
    isToggling: enableMutation.isPending || disableMutation.isPending,
  };
}
