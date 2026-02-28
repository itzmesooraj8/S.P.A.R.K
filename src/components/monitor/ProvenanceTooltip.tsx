/**
 * ProvenanceTooltip — shows data-trustworthiness metadata for a Globe event.
 * Renders inline when `visible` is true, positioned relative to its parent.
 */
import React from 'react';
import type { Provenance } from '../../store/useMonitorStore';

interface Props {
  provenance: Provenance;
  visible: boolean;
  className?: string;
}

function formatAge(cacheAge: number): string {
  if (cacheAge < 0)   return 'unknown';
  if (cacheAge < 60)  return `${cacheAge}s ago`;
  if (cacheAge < 3600) return `${Math.round(cacheAge / 60)}m ago`;
  return `${Math.round(cacheAge / 3600)}h ago`;
}

function methodBadge(method: string): { label: string; color: string } {
  switch (method) {
    case 'http_cached': return { label: 'Cached',    color: 'bg-blue-600/80'   };
    case 'http_live':   return { label: 'Live',      color: 'bg-green-600/80'  };
    case 'ws_push':     return { label: 'Real-time', color: 'bg-purple-600/80' };
    default:            return { label: method,      color: 'bg-gray-600/80'   };
  }
}

export const ProvenanceTooltip: React.FC<Props> = ({ provenance, visible, className = '' }) => {
  if (!visible) return null;

  const { label, color } = methodBadge(provenance.retrievalMethod);
  const ageStr = formatAge(provenance.cacheAge);
  const retrievedAt = new Date(provenance.retrievedAt).toLocaleTimeString();

  return (
    <div
      className={`
        absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2
        w-72 rounded-lg border border-white/10 bg-gray-900/95 backdrop-blur-sm
        shadow-xl text-xs text-gray-200 pointer-events-none
        ${className}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-white/10">
        <span className="font-semibold text-white truncate">{provenance.source}</span>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${color}`}>
          {label}
        </span>
      </div>

      {/* Body */}
      <div className="px-3 py-2 space-y-1">
        <Row label="Provider"    value={provenance.provider} />
        <Row label="Retrieved"   value={retrievedAt} />
        <Row label="Cache age"   value={ageStr} />
        <Row
          label="Source URL"
          value={
            <a
              href={provenance.sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="text-blue-400 hover:text-blue-300 underline underline-offset-2 pointer-events-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {new URL(provenance.sourceUrl).hostname}
            </a>
          }
        />
      </div>

      {/* Tail */}
      <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0
                      border-l-[6px] border-r-[6px] border-t-[6px]
                      border-l-transparent border-r-transparent border-t-gray-900/95" />
    </div>
  );
};

const Row: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div className="flex justify-between gap-2">
    <span className="shrink-0 text-gray-400">{label}</span>
    <span className="text-right text-gray-100 truncate">{value}</span>
  </div>
);
