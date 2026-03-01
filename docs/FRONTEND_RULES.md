# SPARK Frontend Rules
## Selector Stability · WS Hygiene · State Mutation Contracts

These rules exist to prevent a specific class of bug that is **invisible in dev but catastrophic in production**: React's `useSyncExternalStore` double-snapshot check causing infinite render loops, ghost WS listeners stacking reconnect timers, and in-place state mutations causing missed updates.

---

## 1. Zustand Selector Rules

### ❌ Never allocate inside a selector

```ts
// BAD — creates a new array reference on every snapshot check
const tools = useToolStore(s => Array.from(s.pendingTools));
const active = useAlertStore(s => s.alerts.filter(a => !a.dismissed));
const mapped = useEventStore(s => s.events.map(e => e.id));
const obj    = useStore(s => ({ cpu: s.cpu, ram: s.ram }));  // new object ref
```

**Why**: React 18's `useSyncExternalStore` (which Zustand uses internally) calls `getSnapshot()` twice per render for tearing detection. If the selector returns a new reference each time — even with identical contents — React treats the store as "changed" → schedules a re-render → repeats forever → `Maximum update depth exceeded`.

### ✅ Return primitives or stable references

```ts
// GOOD — primitives: Object.is() stable
const count     = useAlertStore(s => s.alerts.filter(a => !a.dismissed).length);
const isOnline  = useConnectionStore(s => s.coreOnline);

// GOOD — stable ref from store (the Set itself, not a copy)
const toolSet   = useToolStore(s => s.pendingTools);

// GOOD — use .find() not .filter()[0]
const lastAlert = useAlertStore(s => s.alerts.find(a => !a.dismissed) ?? null);
```

### ✅ Derive arrays/objects outside the selector with `useMemo`

```ts
// GOOD — Array.from called by useMemo, not the selector
const pendingSet = useToolStore(s => s.pendingTools);    // stable Set ref
const pending    = useMemo(() => Array.from(pendingSet), [pendingSet]);
```

### ✅ Use equality functions only when unavoidable

```ts
import { shallow } from 'zustand/shallow';

// When you must return an object, tell Zustand how to compare it
const { cpu, ram } = useMetricsStore(s => ({ cpu: s.cpu, ram: s.ram }), shallow);
```

---

## 2. State Mutation Contract

### ❌ Never mutate Set/Map/Array in-place in Zustand actions

```ts
// BAD — mutates in place; subscribers may not detect the change
set(s => { s.pendingTools.add(tool); return s; });
```

### ✅ Always produce a new reference for Set/Map/Array

```ts
// GOOD
set(s => ({ pendingTools: new Set([...s.pendingTools, tool]) }));
set(s => ({ pendingTools: new Set(s.pendingTools).add(tool) }));  // same effect
```

---

## 3. Render-Path Stability

### ❌ Never call these in component render or return values

| Expression | Why dangerous |
|---|---|
| `Date.now()` | Changes every millisecond — every render produces a new value |
| `Math.random()` | Non-deterministic; breaks React reconciliation |
| `{ ... }` object literals in JSX props (with selector data) | New reference every render |
| `Array.from(...)` at top-level hook scope | New array every render |

### ✅ Use refs or memo for these values

```ts
const idRef = useRef(`id-${Date.now()}`);        // stable across renders
const id    = useMemo(() => `id-${Date.now()}`, []); // computed once
```

---

## 4. WebSocket Hook Rules

Every WS hook must satisfy all five properties:

### 4.1 Single-instance guard

```ts
const connect = useCallback(() => {
  if (!mountedRef.current) return;
  if (ws.current && ws.current.readyState <= WebSocket.OPEN) return;  // ← required
  // ...
}, [...]);
```

### 4.2 Mounted guard on `onopen`

```ts
socket.onopen = () => {
  if (!mountedRef.current) { socket.close(); return; }  // ← required
  // ...
};
```

### 4.3 Cleanup on unmount

```ts
useEffect(() => {
  mountedRef.current = true;
  connect();
  return () => {
    mountedRef.current = false;
    stopPing?.();
    ws.current?.close(1000, 'component unmount');  // ← required
  };
}, [connect]);
```

### 4.4 Reconnect timer cannot stack

```ts
socket.onclose = () => {
  if (!mountedRef.current) return;  // ← stops timers after unmount
  const delay = ...;
  setTimeout(connect, delay);       // connect() has readyState guard → safe
};
```

### 4.5 Console logs are gated

```ts
// At module level — default: silent
const VERBOSE_WS = import.meta.env.VITE_VERBOSE_WS === 'true';
const wsLog  = (...a: unknown[]) => VERBOSE_WS && console.log('[Tag WS]',  ...a);
const wsWarn = (...a: unknown[]) => VERBOSE_WS && console.warn('[Tag WS]', ...a);
const wsErr  = (...a: unknown[]) => VERBOSE_WS && console.error('[Tag WS]', ...a);
```

Enable via `.env`: `VITE_VERBOSE_WS=true`

---

## 5. Approved Selector Patterns (Quick Reference)

```ts
// ✅ Primitive
const count = useStore(s => s.items.length);
const flag  = useStore(s => s.enabled);
const str   = useStore(s => s.name);

// ✅ Action (functions are always stable references)
const addAlert = useAlertStore(s => s.addAlert);

// ✅ Raw stable store reference (array/set/map stored in state)
const items  = useStore(s => s.items);  // subscribe to the whole array ref

// ✅ Derived via useMemo
const pending = useStore(s => s.pendingTools);
const list    = useMemo(() => Array.from(pending), [pending]);

// ✅ Single object element via .find()
const alert = useAlertStore(s => s.alerts.find(a => a.id === id) ?? null);

// ✅ Multiple primitives with shallow compare (when you must use an object)
const { cpu, ram } = useMetricsStore(s => ({ cpu: s.cpu, ram: s.ram }), shallow);
```
