/**
 * Global Zustand store for World Monitor V2.
 * Manages monitor mode, map view state, AI copilot, and panel visibility.
 */
import { create } from 'zustand';

export type MonitorMode = 'world' | 'tech' | 'finance' | 'happy';

export interface ViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
  transitionDuration: number;
}

export interface MonitorState {
  // Core state
  mode: MonitorMode;
  viewState: ViewState;
  selectedEventId: string | null;

  // AI Core
  aiCoreExpanded: boolean;
  aiMessages: { role: 'user' | 'ai'; content: string }[];

  // Panel visibility
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;

  // Actions
  setMode: (mode: MonitorMode) => void;
  flyTo: (lng: number, lat: number, zoom?: number) => void;
  selectEvent: (id: string | null) => void;
  toggleAICore: () => void;
  addAIMessage: (role: 'user' | 'ai', content: string) => void;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  setViewState: (vs: ViewState) => void;
}

/** Default camera: shows Africa/Europe centered, tilted */
const DEFAULT_VIEW: ViewState = {
  longitude: 20,
  latitude: 25,
  zoom: 2.2,
  pitch: 35,
  bearing: 0,
  transitionDuration: 0,
};

export const useMonitorStore = create<MonitorState>((set) => ({
  mode: 'world',
  viewState: DEFAULT_VIEW,
  selectedEventId: null,
  aiCoreExpanded: false,
  aiMessages: [],
  leftPanelOpen: true,
  rightPanelOpen: true,

  setMode: (mode) => set({ mode, selectedEventId: null }),

  flyTo: (longitude, latitude, zoom = 5) =>
    set({
      viewState: {
        longitude,
        latitude,
        zoom,
        pitch: 45,
        bearing: 0,
        transitionDuration: 2000,
      },
    }),

  selectEvent: (id) => set({ selectedEventId: id }),

  toggleAICore: () => set((s) => ({ aiCoreExpanded: !s.aiCoreExpanded })),

  addAIMessage: (role, content) =>
    set((s) => ({ aiMessages: [...s.aiMessages, { role, content }] })),

  toggleLeftPanel: () => set((s) => ({ leftPanelOpen: !s.leftPanelOpen })),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),

  setViewState: (vs) => set({ viewState: { ...vs, transitionDuration: 0 } }),
}));
