/**
 * SPARK Context Store (Zustand)
 * ────────────────────────────────────────────────────────────────────────────────
 * Global context for Command Bar and Intent Router.
 * Tracks: active module, selected item, recent alerts, search results, mode.
 */

import { create } from 'zustand';

export interface SelectedItem {
  module: string;  // 'globe', 'security', 'neural_search', 'music', 'browser', 'agent'
  type: string;    // 'earthquake', 'alert', 'search_result', 'track', 'history', etc.
  label: string;   // Human-readable: "M6.2 Earthquake, Southern Japan"
  data: Record<string, any>;  // Full data object for context enrichment
}

export interface AlertItem {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  source: string;  // 'security', 'system', 'agent', etc.
  timestamp: number;
}

export interface ContextStoreState {
  // Active module in the HUD
  activeModule: string | null;
  setActiveModule: (module: string | null) => void;

  // Currently selected item (for pronoun resolution)
  selectedItem: SelectedItem | null;
  setSelectedItem: (item: SelectedItem | null) => void;

  // Most recent system alert
  lastAlert: AlertItem | null;
  setLastAlert: (alert: AlertItem | null) => void;

  // Result of the last tool/agent execution
  lastToolResult: any;
  setLastToolResult: (result: any) => void;

  // Last neural search query and results
  lastSearchQuery: string | null;
  lastSearchResults: any[];
  setLastSearch: (query: string, results: any[]) => void;

  // Current mode/routine
  currentMode: string | null;
  setCurrentMode: (mode: string | null) => void;

  // Utility: Get context description for the Command Bar
  getContextLabel: () => string;

  // Clear all context
  clear: () => void;
}

export const useContextStore = create<ContextStoreState>((set, get) => ({
  activeModule: null,
  setActiveModule: (module) => set({ activeModule: module }),

  selectedItem: null,
  setSelectedItem: (item) => set({ selectedItem: item }),

  lastAlert: null,
  setLastAlert: (alert) => set({ lastAlert: alert }),

  lastToolResult: null,
  setLastToolResult: (result) => set({ lastToolResult: result }),

  lastSearchQuery: null,
  lastSearchResults: [],
  setLastSearch: (query, results) => set({
    lastSearchQuery: query,
    lastSearchResults: results,
  }),

  currentMode: null,
  setCurrentMode: (mode) => set({ currentMode: mode }),

  getContextLabel: () => {
    const state = get();
    if (state.selectedItem) {
      return `${state.selectedItem.module} · ${state.selectedItem.label}`;
    }
    if (state.lastAlert) {
      return `Alert · ${state.lastAlert.message}`;
    }
    if (state.activeModule) {
      return `Viewing ${state.activeModule}`;
    }
    return '';
  },

  clear: () => set({
    activeModule: null,
    selectedItem: null,
    lastAlert: null,
    lastToolResult: null,
    lastSearchQuery: null,
    lastSearchResults: [],
    currentMode: null,
  }),
}));
