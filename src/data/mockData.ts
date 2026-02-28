/**
 * Comprehensive mock datasets for all 4 monitor modes.
 * Real-world coordinates, realistic event data, and market tickers.
 */
import type { MonitorMode } from '@/store/useMonitorStore';

// ========== TYPES ==========
export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface MonitorEvent {
  id: string;
  title: string;
  location: string;
  lat: number;
  lng: number;
  severity: Severity;
  category: string;
  timestamp: 'today' | 'yesterday' | 'this_week';
  description: string;
}

export interface CountryRisk {
  id: string;
  name: string;
  riskScore: number;
  lat: number;
  lng: number;
  sparklineData: number[];
  trend: 'up' | 'down' | 'stable';
}

export interface TickerItem {
  symbol: string;
  value: number;
  delta: number;
  deltaPercent: number;
}

export interface ArcConnection {
  source: [number, number]; // [lng, lat]
  target: [number, number];
}

// ========== WORLD MODE EVENTS ==========
const worldEvents: MonitorEvent[] = [
  { id: 'w1', title: 'Eastern Front Escalation', location: 'Donetsk, Ukraine', lat: 48.0, lng: 37.8, severity: 'critical', category: 'conflict', timestamp: 'today', description: 'Heavy artillery exchanges' },
  { id: 'w2', title: 'Naval Exercises Detected', location: 'Black Sea', lat: 43.5, lng: 34.0, severity: 'high', category: 'conflict', timestamp: 'today', description: 'Fleet repositioning observed' },
  { id: 'w3', title: 'Gaza Humanitarian Crisis', location: 'Gaza Strip', lat: 31.35, lng: 34.31, severity: 'critical', category: 'conflict', timestamp: 'today', description: 'Aid corridors restricted' },
  { id: 'w4', title: 'Taiwan Strait Patrol', location: 'Taiwan Strait', lat: 24.5, lng: 119.5, severity: 'high', category: 'conflict', timestamp: 'today', description: 'PLA Navy vessels detected' },
  { id: 'w5', title: 'M6.2 Earthquake', location: 'Papua New Guinea', lat: -6.1, lng: 147.0, severity: 'medium', category: 'earthquake', timestamp: 'today', description: 'Depth 35km, tsunami watch' },
  { id: 'w6', title: 'Sahel Insurgency Attack', location: 'Burkina Faso', lat: 12.3, lng: -1.5, severity: 'high', category: 'conflict', timestamp: 'yesterday', description: 'Military outpost targeted' },
  { id: 'w7', title: 'Sudan Civil Conflict', location: 'Khartoum, Sudan', lat: 15.6, lng: 32.5, severity: 'critical', category: 'conflict', timestamp: 'yesterday', description: 'RSF advance on capital' },
  { id: 'w8', title: 'Myanmar Resistance Gains', location: 'Shan State, Myanmar', lat: 21.0, lng: 97.0, severity: 'medium', category: 'conflict', timestamp: 'yesterday', description: 'Resistance captures territory' },
  { id: 'w9', title: 'Yemen Missile Launch', location: 'Red Sea', lat: 14.5, lng: 42.5, severity: 'high', category: 'conflict', timestamp: 'yesterday', description: 'Anti-ship missile intercepted' },
  { id: 'w10', title: 'M5.8 Earthquake', location: 'Eastern Türkiye', lat: 38.4, lng: 38.3, severity: 'medium', category: 'earthquake', timestamp: 'this_week', description: 'Minor structural damage' },
  { id: 'w11', title: 'South China Sea Standoff', location: 'Spratly Islands', lat: 10.0, lng: 114.0, severity: 'medium', category: 'conflict', timestamp: 'this_week', description: 'PH-CN vessel confrontation' },
  { id: 'w12', title: 'Ethiopia Border Tensions', location: 'Tigray, Ethiopia', lat: 13.5, lng: 39.5, severity: 'medium', category: 'political', timestamp: 'this_week', description: 'Ceasefire violations' },
  { id: 'w13', title: 'Arctic Military Buildup', location: 'Svalbard, Norway', lat: 78.2, lng: 15.6, severity: 'low', category: 'conflict', timestamp: 'this_week', description: 'NATO monitoring Russian bases' },
  { id: 'w14', title: 'Libya Political Crisis', location: 'Tripoli, Libya', lat: 32.9, lng: 13.2, severity: 'medium', category: 'political', timestamp: 'this_week', description: 'Government factions clash' },
];

// ========== TECH MODE EVENTS ==========
const techEvents: MonitorEvent[] = [
  { id: 't1', title: 'GPT-5 Training Detected', location: 'San Francisco, USA', lat: 37.77, lng: -122.42, severity: 'high', category: 'tech', timestamp: 'today', description: 'Massive compute cluster active' },
  { id: 't2', title: 'Critical Zero-Day Exploit', location: 'Moscow, Russia', lat: 55.75, lng: 37.62, severity: 'critical', category: 'cyber', timestamp: 'today', description: 'CVE affecting infrastructure' },
  { id: 't3', title: 'TSMC Fab Disruption', location: 'Hsinchu, Taiwan', lat: 24.8, lng: 120.97, severity: 'high', category: 'tech', timestamp: 'today', description: 'Production line halt' },
  { id: 't4', title: 'DDoS on EU Banking', location: 'Frankfurt, Germany', lat: 50.1, lng: 8.68, severity: 'critical', category: 'cyber', timestamp: 'today', description: '400Gbps attack sustained' },
  { id: 't5', title: 'DeepMind Breakthrough', location: 'London, UK', lat: 51.51, lng: -0.13, severity: 'low', category: 'tech', timestamp: 'yesterday', description: 'AlphaFold 4 published' },
  { id: 't6', title: 'Ransomware Wave', location: 'Singapore', lat: 1.35, lng: 103.82, severity: 'high', category: 'cyber', timestamp: 'yesterday', description: 'Healthcare systems hit' },
  { id: 't7', title: 'Quantum Compute Milestone', location: 'Zurich, Switzerland', lat: 47.38, lng: 8.54, severity: 'medium', category: 'tech', timestamp: 'yesterday', description: 'IBM 1000+ qubit processor' },
  { id: 't8', title: 'Undersea Cable Damage', location: 'Baltic Sea', lat: 57.0, lng: 20.0, severity: 'high', category: 'cyber', timestamp: 'this_week', description: 'Suspected sabotage' },
  { id: 't9', title: 'AI Regulation Vote', location: 'Brussels, Belgium', lat: 50.85, lng: 4.35, severity: 'medium', category: 'political', timestamp: 'this_week', description: 'EU AI Act enforcement' },
  { id: 't10', title: 'Hyperscale Datacenter Online', location: 'Singapore', lat: 1.3, lng: 103.8, severity: 'low', category: 'tech', timestamp: 'this_week', description: 'New 200MW facility' },
  { id: 't11', title: 'State-Sponsored Campaign', location: 'Pyongyang, DPRK', lat: 39.03, lng: 125.75, severity: 'critical', category: 'cyber', timestamp: 'this_week', description: 'Lazarus Group active' },
];

// ========== FINANCE MODE EVENTS ==========
const financeEvents: MonitorEvent[] = [
  { id: 'f1', title: 'Fed Rate Decision', location: 'Washington DC, USA', lat: 38.9, lng: -77.04, severity: 'critical', category: 'economic', timestamp: 'today', description: 'Markets pricing 75% hold' },
  { id: 'f2', title: 'BTC Whale Movement', location: 'Zurich, Switzerland', lat: 47.37, lng: 8.54, severity: 'high', category: 'economic', timestamp: 'today', description: '$2.3B cold wallet transfer' },
  { id: 'f3', title: 'Nikkei Circuit Breaker', location: 'Tokyo, Japan', lat: 35.68, lng: 139.65, severity: 'critical', category: 'economic', timestamp: 'today', description: 'Trading halt triggered' },
  { id: 'f4', title: 'Yuan Devaluation', location: 'Beijing, China', lat: 39.9, lng: 116.4, severity: 'high', category: 'economic', timestamp: 'today', description: 'PBOC adjusts trading band' },
  { id: 'f5', title: 'Oil Supply Disruption', location: 'Strait of Hormuz', lat: 26.5, lng: 56.3, severity: 'high', category: 'economic', timestamp: 'yesterday', description: 'Tanker route threatened' },
  { id: 'f6', title: 'ECB Emergency Meeting', location: 'Frankfurt, Germany', lat: 50.1, lng: 8.68, severity: 'medium', category: 'economic', timestamp: 'yesterday', description: 'Bond spread widening' },
  { id: 'f7', title: 'Gold Record High', location: 'London, UK', lat: 51.51, lng: -0.13, severity: 'medium', category: 'economic', timestamp: 'yesterday', description: 'Safe haven demand surge' },
  { id: 'f8', title: 'EM Debt Crisis Signal', location: 'Buenos Aires, Argentina', lat: -34.6, lng: -58.38, severity: 'high', category: 'economic', timestamp: 'this_week', description: 'Bond yields at 25%' },
  { id: 'f9', title: 'Crypto Exchange Collapse', location: 'Dubai, UAE', lat: 25.2, lng: 55.27, severity: 'critical', category: 'economic', timestamp: 'this_week', description: '$800M frozen assets' },
  { id: 'f10', title: 'Trade War Escalation', location: 'Washington DC, USA', lat: 38.9, lng: -77.04, severity: 'high', category: 'political', timestamp: 'this_week', description: 'New tariff package' },
];

// ========== HAPPY MODE EVENTS ==========
const happyEvents: MonitorEvent[] = [
  { id: 'h1', title: 'Amazon Reforestation Record', location: 'Manaus, Brazil', lat: -3.12, lng: -60.02, severity: 'low', category: 'positive', timestamp: 'today', description: '50K hectares restored' },
  { id: 'h2', title: 'Great Barrier Reef Recovery', location: 'Queensland, Australia', lat: -18.29, lng: 147.7, severity: 'low', category: 'positive', timestamp: 'today', description: 'Coral at 10-year high' },
  { id: 'h3', title: 'Iceland 100% Renewable', location: 'Reykjavik, Iceland', lat: 64.15, lng: -21.94, severity: 'low', category: 'positive', timestamp: 'today', description: 'Full renewable grid' },
  { id: 'h4', title: 'Panda Population Surge', location: 'Chengdu, China', lat: 30.57, lng: 104.07, severity: 'low', category: 'positive', timestamp: 'yesterday', description: 'Wild population up 17%' },
  { id: 'h5', title: 'Ocean Cleanup Milestone', location: 'Pacific Ocean', lat: 30.0, lng: -140.0, severity: 'low', category: 'positive', timestamp: 'yesterday', description: '200 tons plastic removed' },
  { id: 'h6', title: 'Solar Capacity Record', location: 'Rajasthan, India', lat: 26.9, lng: 70.9, severity: 'low', category: 'positive', timestamp: 'yesterday', description: 'World largest solar farm' },
  { id: 'h7', title: 'Regional Peace Agreement', location: 'Addis Ababa, Ethiopia', lat: 9.0, lng: 38.75, severity: 'low', category: 'positive', timestamp: 'this_week', description: 'Ceasefire holding strong' },
  { id: 'h8', title: 'Malaria Vaccine Rollout', location: 'Accra, Ghana', lat: 5.6, lng: -0.19, severity: 'low', category: 'positive', timestamp: 'this_week', description: '10M doses distributed' },
  { id: 'h9', title: 'North Sea Wind Farm', location: 'North Sea', lat: 56.0, lng: 3.0, severity: 'low', category: 'positive', timestamp: 'this_week', description: '3.6GW capacity online' },
  { id: 'h10', title: 'Orangutan Recovery', location: 'Borneo, Indonesia', lat: 0.96, lng: 114.55, severity: 'low', category: 'positive', timestamp: 'this_week', description: 'Population stabilized' },
];

// ========== EVENT ACCESSOR ==========
export const getEventsForMode = (mode: MonitorMode): MonitorEvent[] => {
  switch (mode) {
    case 'world': return worldEvents;
    case 'tech': return techEvents;
    case 'finance': return financeEvents;
    case 'happy': return happyEvents;
  }
};

// ========== ARC CONNECTIONS ==========
const worldArcs: ArcConnection[] = [
  { source: [37.62, 55.75], target: [37.8, 48.0] },
  { source: [-77.04, 38.9], target: [15.6, 78.2] },
  { source: [-77.04, 38.9], target: [119.5, 24.5] },
  { source: [37.62, 55.75], target: [34.0, 43.5] },
  { source: [119.5, 24.5], target: [114.0, 10.0] },
  { source: [44.4, 33.3], target: [42.5, 14.5] },
  { source: [-77.04, 38.9], target: [32.5, 15.6] },
  { source: [36.8, 34.8], target: [34.31, 31.35] },
];

const techArcs: ArcConnection[] = [
  { source: [37.62, 55.75], target: [8.68, 50.1] },
  { source: [125.75, 39.03], target: [-122.42, 37.77] },
  { source: [-122.42, 37.77], target: [-0.13, 51.51] },
  { source: [-122.42, 37.77], target: [120.97, 24.8] },
  { source: [103.82, 1.35], target: [8.68, 50.1] },
  { source: [37.62, 55.75], target: [20.0, 57.0] },
  { source: [-0.13, 51.51], target: [8.54, 47.38] },
  { source: [4.35, 50.85], target: [-122.42, 37.77] },
];

const financeArcs: ArcConnection[] = [
  { source: [-74.0, 40.71], target: [139.65, 35.68] },
  { source: [-74.0, 40.71], target: [-0.13, 51.51] },
  { source: [116.4, 39.9], target: [114.17, 22.32] },
  { source: [-77.04, 38.9], target: [116.4, 39.9] },
  { source: [8.54, 47.37], target: [55.27, 25.2] },
  { source: [-0.13, 51.51], target: [8.68, 50.1] },
  { source: [56.3, 26.5], target: [-0.13, 51.51] },
  { source: [-58.38, -34.6], target: [-74.0, 40.71] },
];

const happyArcs: ArcConnection[] = [
  { source: [-60.02, -3.12], target: [-77.04, 38.9] },
  { source: [-21.94, 64.15], target: [8.68, 50.1] },
  { source: [70.9, 26.9], target: [103.82, 1.35] },
  { source: [3.0, 56.0], target: [-0.13, 51.51] },
  { source: [-0.19, 5.6], target: [36.8, -1.3] },
  { source: [38.75, 9.0], target: [32.5, 15.6] },
];

export const getArcsForMode = (mode: MonitorMode): ArcConnection[] => {
  switch (mode) {
    case 'world': return worldArcs;
    case 'tech': return techArcs;
    case 'finance': return financeArcs;
    case 'happy': return happyArcs;
  }
};

// ========== MARKET TICKERS ==========
const worldTicker: TickerItem[] = [
  { symbol: 'VIX', value: 28.45, delta: 3.2, deltaPercent: 12.67 },
  { symbol: 'GOLD', value: 2847.30, delta: 24.50, deltaPercent: 0.87 },
  { symbol: 'OIL', value: 89.72, delta: -1.34, deltaPercent: -1.47 },
  { symbol: 'DXY', value: 106.23, delta: 0.45, deltaPercent: 0.42 },
  { symbol: 'UST10Y', value: 4.67, delta: 0.08, deltaPercent: 1.74 },
  { symbol: 'S&P500', value: 5234.18, delta: -45.67, deltaPercent: -0.86 },
  { symbol: 'WHEAT', value: 612.50, delta: 8.25, deltaPercent: 1.36 },
];

const techTicker: TickerItem[] = [
  { symbol: 'NVDA', value: 924.50, delta: 12.30, deltaPercent: 1.35 },
  { symbol: 'MSFT', value: 442.87, delta: -3.45, deltaPercent: -0.77 },
  { symbol: 'GOOG', value: 178.23, delta: 2.10, deltaPercent: 1.19 },
  { symbol: 'META', value: 512.40, delta: 8.90, deltaPercent: 1.77 },
  { symbol: 'BTC', value: 67845.00, delta: 1234.00, deltaPercent: 1.85 },
  { symbol: 'ETH', value: 3456.78, delta: -89.00, deltaPercent: -2.51 },
  { symbol: 'SOL', value: 187.45, delta: 5.67, deltaPercent: 3.12 },
];

const financeTicker: TickerItem[] = [
  { symbol: 'S&P500', value: 5234.18, delta: -45.67, deltaPercent: -0.86 },
  { symbol: 'NIKKEI', value: 38456.00, delta: -823.00, deltaPercent: -2.09 },
  { symbol: 'FTSE', value: 8134.50, delta: 23.40, deltaPercent: 0.29 },
  { symbol: 'EUR/USD', value: 1.0834, delta: -0.0023, deltaPercent: -0.21 },
  { symbol: 'GBP/USD', value: 1.2645, delta: 0.0012, deltaPercent: 0.09 },
  { symbol: 'GOLD', value: 2847.30, delta: 24.50, deltaPercent: 0.87 },
  { symbol: 'BTC', value: 67845.00, delta: 1234.00, deltaPercent: 1.85 },
];

const happyTicker: TickerItem[] = [
  { symbol: 'CLEAN', value: 1247.80, delta: 15.30, deltaPercent: 1.24 },
  { symbol: 'CARBON', value: 72.45, delta: -2.10, deltaPercent: -2.82 },
  { symbol: 'ESG', value: 324.67, delta: 4.56, deltaPercent: 1.42 },
  { symbol: 'SOLAR', value: 89.34, delta: 1.23, deltaPercent: 1.40 },
  { symbol: 'WIND', value: 156.78, delta: 3.45, deltaPercent: 2.25 },
  { symbol: 'H2O', value: 45.23, delta: 0.67, deltaPercent: 1.50 },
  { symbol: 'FOREST', value: 892.10, delta: 12.30, deltaPercent: 1.40 },
];

export const getTickerForMode = (mode: MonitorMode): TickerItem[] => {
  switch (mode) {
    case 'world': return worldTicker;
    case 'tech': return techTicker;
    case 'finance': return financeTicker;
    case 'happy': return happyTicker;
  }
};

// ========== COUNTRY INSTABILITY INDEX ==========
export const countries: CountryRisk[] = [
  { id: 'ua', name: 'Ukraine', riskScore: 95, lat: 48.38, lng: 31.17, sparklineData: [78, 82, 88, 85, 90, 93, 95], trend: 'up' },
  { id: 'sd', name: 'Sudan', riskScore: 92, lat: 15.5, lng: 32.5, sparklineData: [70, 75, 80, 85, 88, 90, 92], trend: 'up' },
  { id: 'ps', name: 'Palestine', riskScore: 90, lat: 31.9, lng: 35.2, sparklineData: [60, 65, 72, 80, 85, 88, 90], trend: 'up' },
  { id: 'mm', name: 'Myanmar', riskScore: 85, lat: 19.76, lng: 96.08, sparklineData: [80, 82, 83, 84, 84, 85, 85], trend: 'stable' },
  { id: 'ye', name: 'Yemen', riskScore: 83, lat: 15.37, lng: 44.19, sparklineData: [85, 84, 83, 82, 82, 83, 83], trend: 'stable' },
  { id: 'so', name: 'Somalia', riskScore: 80, lat: 5.15, lng: 46.2, sparklineData: [78, 79, 80, 80, 80, 81, 80], trend: 'stable' },
  { id: 'sy', name: 'Syria', riskScore: 78, lat: 34.8, lng: 38.99, sparklineData: [82, 80, 79, 78, 78, 78, 78], trend: 'down' },
  { id: 'af', name: 'Afghanistan', riskScore: 76, lat: 33.94, lng: 67.71, sparklineData: [80, 79, 78, 77, 76, 76, 76], trend: 'down' },
  { id: 'ly', name: 'Libya', riskScore: 72, lat: 26.34, lng: 17.23, sparklineData: [65, 68, 70, 71, 72, 72, 72], trend: 'up' },
  { id: 'et', name: 'Ethiopia', riskScore: 68, lat: 9.15, lng: 40.49, sparklineData: [72, 71, 70, 69, 68, 68, 68], trend: 'down' },
  { id: 'ht', name: 'Haiti', riskScore: 65, lat: 18.97, lng: -72.28, sparklineData: [58, 60, 62, 63, 64, 65, 65], trend: 'up' },
  { id: 'cd', name: 'DR Congo', riskScore: 63, lat: -4.04, lng: 21.76, sparklineData: [60, 61, 62, 62, 63, 63, 63], trend: 'stable' },
  { id: 'bf', name: 'Burkina Faso', riskScore: 60, lat: 12.36, lng: -1.52, sparklineData: [50, 53, 55, 57, 58, 59, 60], trend: 'up' },
  { id: 'ml', name: 'Mali', riskScore: 58, lat: 17.57, lng: -4.0, sparklineData: [55, 56, 57, 57, 58, 58, 58], trend: 'stable' },
  { id: 'pk', name: 'Pakistan', riskScore: 52, lat: 30.38, lng: 69.35, sparklineData: [48, 49, 50, 51, 51, 52, 52], trend: 'up' },
  { id: 'iq', name: 'Iraq', riskScore: 48, lat: 33.22, lng: 43.68, sparklineData: [55, 53, 51, 50, 49, 48, 48], trend: 'down' },
  { id: 'ng', name: 'Nigeria', riskScore: 45, lat: 9.08, lng: 7.49, sparklineData: [42, 43, 44, 44, 45, 45, 45], trend: 'stable' },
  { id: 've', name: 'Venezuela', riskScore: 42, lat: 6.42, lng: -66.59, sparklineData: [48, 46, 45, 44, 43, 42, 42], trend: 'down' },
  { id: 'lb', name: 'Lebanon', riskScore: 40, lat: 33.85, lng: 35.86, sparklineData: [45, 44, 43, 42, 41, 40, 40], trend: 'down' },
  { id: 'mx', name: 'Mexico', riskScore: 35, lat: 23.63, lng: -102.55, sparklineData: [32, 33, 34, 34, 35, 35, 35], trend: 'stable' },
];
