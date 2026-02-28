/**
 * useSnapshotStore — IndexedDB persistence for Globe Monitor snapshots.
 *
 * Snapshots contain a full dump of real-time data at a point in time.
 * Metadata (id, label, createdAt, eventCount, mode) is kept in Zustand/localStorage.
 * Full event data lives in IndexedDB to avoid localStorage size limits.
 *
 * Retention: last 50 snapshots (auto-pruned on save).
 */
import { useCallback } from 'react';
import { useMonitorStore } from '@/store/useMonitorStore';
import type { RealEvent, RealFireEvent, RealTicker, MonitorMode } from '@/store/useMonitorStore';

const DB_NAME    = 'spark-monitor-snapshots';
const STORE_NAME = 'snapshots';
const DB_VERSION = 1;

export interface SnapshotData {
  id: string;
  mode: MonitorMode;
  createdAt: number;
  events: RealEvent[];
  fireEvents: RealFireEvent[];
  tickers: RealTicker[];
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = (e.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

async function idbPut(data: SnapshotData): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.put(data);
    tx.oncomplete = () => resolve();
    tx.onerror    = () => reject(tx.error);
  });
}

async function idbGet(id: string): Promise<SnapshotData | undefined> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req   = store.get(id);
    req.onsuccess = () => resolve(req.result);
    req.onerror   = () => reject(req.error);
  });
}

async function idbDelete(id: string): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx    = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror    = () => reject(tx.error);
  });
}

export function useSnapshotStore() {
  const addSnapshotMeta    = useMonitorStore((s) => s.addSnapshotMeta);
  const removeSnapshotMeta = useMonitorStore((s) => s.removeSnapshotMeta);
  const snapshots          = useMonitorStore((s) => s.snapshots);
  const setPlaybackIndex   = useMonitorStore((s) => s.setPlaybackIndex);
  const playbackIndex      = useMonitorStore((s) => s.playbackIndex);

  /** Save current live data as a named snapshot */
  const saveSnapshot = useCallback(async (label?: string) => {
    const s = useMonitorStore.getState();
    const id = `snap-${Date.now()}`;
    const data: SnapshotData = {
      id,
      mode:       s.mode,
      createdAt:  Date.now(),
      events:     [...s.realEvents, ...s.realWorldEvents],
      fireEvents: s.realFireEvents,
      tickers:    s.realMarketTickers,
    };
    await idbPut(data);
    addSnapshotMeta({
      id,
      label: label || new Date().toISOString().slice(0, 19).replace('T', ' '),
      createdAt: data.createdAt,
      eventCount: data.events.length,
      mode: s.mode,
    });
    // Prune old snapshots > 50
    const metas = useMonitorStore.getState().snapshots;
    if (metas.length > 50) {
      const oldest = metas[0];
      await idbDelete(oldest.id);
      removeSnapshotMeta(oldest.id);
    }
    return id;
  }, [addSnapshotMeta, removeSnapshotMeta]);

  /** Load a snapshot from IndexedDB for playback */
  const loadSnapshot = useCallback(async (id: string): Promise<SnapshotData | undefined> => {
    return idbGet(id);
  }, []);

  /** Remove a snapshot */
  const deleteSnapshot = useCallback(async (id: string) => {
    await idbDelete(id);
    removeSnapshotMeta(id);
    if (playbackIndex !== null && snapshots[playbackIndex]?.id === id) {
      setPlaybackIndex(null);
    }
  }, [removeSnapshotMeta, playbackIndex, snapshots, setPlaybackIndex]);

  return { snapshots, playbackIndex, setPlaybackIndex, saveSnapshot, loadSnapshot, deleteSnapshot };
}
