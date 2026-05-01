export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical';

export interface MonitorEvent {
  id: string;
  title: string;
  category: string;
  severity: SeverityLevel;
  lat: number;
  lng: number;
  timestamp?: string;
  location?: string;
  fetchedAt?: number;
  [key: string]: unknown;
}

export interface MonitorArc {
  source: [number, number];
  target: [number, number];
}

export interface TickerItem {
  symbol: string;
  value: number;
  deltaPercent: number;
}

export interface CountryRisk {
  id: string;
  name: string;
  riskScore: number;
  lat: number;
  lng: number;
  sparklineData: number[];
}

const EMPTY_EVENTS: Record<string, MonitorEvent[]> = {
  world: [],
  tech: [],
  finance: [],
  happy: [],
};

const EMPTY_ARCS: Record<string, MonitorArc[]> = {
  world: [],
  tech: [],
  finance: [],
  happy: [],
};

const EMPTY_TICKERS: Record<string, TickerItem[]> = {
  world: [],
  tech: [],
  finance: [],
  happy: [],
};

export function getEventsForMode(mode: string): MonitorEvent[] {
  return [...(EMPTY_EVENTS[mode] || [])];
}

export function getArcsForMode(mode: string): MonitorArc[] {
  return [...(EMPTY_ARCS[mode] || [])];
}

export function getTickerForMode(mode: string): TickerItem[] {
  return [...(EMPTY_TICKERS[mode] || [])];
}

export const countries: CountryRisk[] = [];
