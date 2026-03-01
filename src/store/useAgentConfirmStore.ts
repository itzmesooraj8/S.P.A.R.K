/**
 * useAgentConfirmStore
 * ─────────────────────────────────────────────────────────────────────────────
 * Holds the current pending CONFIRM_TOOL request from the Desktop Agent.
 * HudLayout reads this to display AgentConfirmModal.
 */

import { create } from 'zustand';
import { ConfirmRequest } from '@/components/hud/AgentConfirmModal';

interface AgentConfirmStore {
  pendingRequest: ConfirmRequest | null;
  setPending: (req: ConfirmRequest | null) => void;
}

export const useAgentConfirmStore = create<AgentConfirmStore>((set) => ({
  pendingRequest: null,
  setPending: (req) => set({ pendingRequest: req }),
}));
