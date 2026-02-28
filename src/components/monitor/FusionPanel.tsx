/**
 * FusionPanel — SPARK Signal Fusion: "Why This Matters" intelligence cards.
 *
 * Calls /api/globe/v1/getFusionSummary (new clean Globe API).
 * Each FusionItem has: title, summary, confidence, cause/effect chain,
 * evidence links, data gaps, entity tags, severity.
 *
 * This is SPARK's key differentiator over World Monitor:
 * not just aggregation, but causal correlation with confidence.
 */
import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, ChevronRight, AlertCircle, ExternalLink } from 'lucide-react';
import { useMonitorStore, type FusionItem, type Severity } from '@/store/useMonitorStore';
import { BasePanel } from './BasePanel';

const CONF_COLOR = (conf: number) => {
  if (conf >= 0.8) return '#34d399';
  if (conf >= 0.6) return '#fbbf24';
  if (conf >= 0.4) return '#fb923c';
  return '#f87171';
};

const SEV_COLORS: Record<Severity, string> = {
  critical: '#f87171',
  high:     '#fb923c',
  medium:   '#fbbf24',
  low:      '#34d399',
};

interface FusionPanelProps {
  accentColor?: string;
}

export const FusionPanel = ({ accentColor = '#a78bfa' }: FusionPanelProps) => {
  const fusionItems   = useMonitorStore((s) => s.fusionItems);
  const fusionLoading = useMonitorStore((s) => s.fusionLoading);
  const lastFetch     = useMonitorStore((s) => s.lastFetch);
  const fetchFusion   = useMonitorStore((s) => s.fetchFusionSummary);

  // Refresh fusion summary whenever main data refreshes
  useEffect(() => {
    if (lastFetch > 0) fetchFusion();
  }, [lastFetch, fetchFusion]);

  // Placeholder items when backend is not yet available
  const displayItems: FusionItem[] = fusionItems.length > 0 ? fusionItems : [
    {
      id: 'fus-demo-1',
      title: 'Seismic Cluster Near Tectonic Boundary',
      summary: 'Three M5+ earthquakes within 200km in 6h suggest possible foreshock sequence near Pacific Ring of Fire.',
      confidence: 0.72,
      evidenceLinks: [],
      entities: ['USGS', 'Pacific Plate'],
      regions: ['Pacific Ocean'],
      cause: 'Tectonic stress accumulation',
      effect: 'Elevated aftershock probability (72h)',
      dataGaps: ['Nearby GPS strain data unavailable'],
      severity: 'high',
      updatedAt: Date.now(),
    },
    {
      id: 'fus-demo-2',
      title: 'Conflict Escalation Pattern Detected',
      summary: 'GDELT conflict event surge (+340%) correlates with military flight increase in same theatre.',
      confidence: 0.61,
      evidenceLinks: [],
      entities: ['GDELT', 'OpenSky'],
      regions: ['Eastern Europe'],
      cause: 'Political instability signal from news volume',
      effect: 'Potential supply chain disruption',
      dataGaps: ['Ground-truth confirmation missing'],
      severity: 'critical',
      updatedAt: Date.now(),
    },
    {
      id: 'fus-demo-3',
      title: 'Wildfire-Drought Compound Risk',
      summary: 'NASA EONET wildfire detections overlap with climate anomaly drought zones, compounding risk rating.',
      confidence: 0.85,
      evidenceLinks: [],
      entities: ['NASA EONET'],
      regions: ['North America'],
      cause: 'Prolonged drought + high FRP readings',
      effect: 'Infrastructure and displacement risk elevated',
      dataGaps: [],
      severity: 'high',
      updatedAt: Date.now(),
    },
  ];

  return (
    <BasePanel
      title="SIGNAL FUSION"
      icon={<Zap size={13} />}
      accentColor={accentColor}
      defaultCollapsed={false}
      badge={
        !fusionLoading && displayItems.length > 0 ? (
          <span className="text-[8px] font-mono font-bold px-1.5 py-0.5 rounded"
            style={{ background: `${accentColor}15`, color: accentColor, border: `1px solid ${accentColor}30` }}>
            {displayItems.length}
          </span>
        ) : undefined
      }
    >
      <div className="space-y-2">
        <p className="text-[8px] font-mono text-foreground/40 leading-relaxed">
          Causal correlation engine · confidence-weighted · SPARK-native
        </p>

        {fusionLoading && (
          <div className="flex items-center gap-2 py-3">
            <div className="w-1.5 h-1.5 rounded-full animate-ping" style={{ background: accentColor }} />
            <span className="text-[9px] font-mono" style={{ color: accentColor }}>
              CORRELATING SIGNALS…
            </span>
          </div>
        )}

        <AnimatePresence initial={false}>
          {displayItems.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded overflow-hidden"
              style={{
                background: 'rgba(255,255,255,0.025)',
                border: `1px solid ${SEV_COLORS[item.severity]}25`,
              }}
            >
              {/* Header row */}
              <div className="flex items-start gap-2 p-2">
                {/* Severity indicator */}
                <span
                  className="w-0.5 self-stretch rounded-full shrink-0"
                  style={{ background: SEV_COLORS[item.severity] }}
                />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    {/* Severity badge */}
                    <span
                      className="text-[7px] font-mono font-bold px-1 rounded"
                      style={{
                        background: `${SEV_COLORS[item.severity]}20`,
                        color: SEV_COLORS[item.severity],
                        border: `1px solid ${SEV_COLORS[item.severity]}40`,
                      }}
                    >
                      {item.severity.toUpperCase()}
                    </span>

                    {/* Confidence meter */}
                    <div className="flex items-center gap-1 ml-auto">
                      <div
                        className="h-1 rounded-full"
                        style={{
                          width: 32,
                          background: 'rgba(255,255,255,0.08)',
                        }}
                      >
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${item.confidence * 100}%`,
                            background: CONF_COLOR(item.confidence),
                          }}
                        />
                      </div>
                      <span
                        className="text-[8px] font-mono font-bold"
                        style={{ color: CONF_COLOR(item.confidence) }}
                      >
                        {Math.round(item.confidence * 100)}%
                      </span>
                    </div>
                  </div>

                  {/* Title */}
                  <p className="text-[10px] font-mono font-bold text-foreground/90 leading-tight mb-1">
                    {item.title}
                  </p>

                  {/* Summary */}
                  <p className="text-[9px] font-mono text-foreground/60 leading-relaxed mb-1.5">
                    {item.summary}
                  </p>

                  {/* Cause → Effect chain */}
                  {(item.cause || item.effect) && (
                    <div className="flex items-start gap-1.5 mb-1.5">
                      {item.cause && (
                        <div className="flex-1 rounded px-1.5 py-1"
                          style={{ background: 'rgba(251,191,36,0.06)', border: '1px solid rgba(251,191,36,0.15)' }}>
                          <p className="text-[7px] font-mono text-foreground/40 mb-0.5">CAUSE</p>
                          <p className="text-[8px] font-mono text-yellow-300/80">{item.cause}</p>
                        </div>
                      )}
                      {item.cause && item.effect && (
                        <ChevronRight size={10} className="mt-3 shrink-0 text-foreground/30" />
                      )}
                      {item.effect && (
                        <div className="flex-1 rounded px-1.5 py-1"
                          style={{ background: 'rgba(248,113,113,0.06)', border: '1px solid rgba(248,113,113,0.15)' }}>
                          <p className="text-[7px] font-mono text-foreground/40 mb-0.5">EFFECT</p>
                          <p className="text-[8px] font-mono text-red-300/80">{item.effect}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Entity tags */}
                  {item.entities.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-1.5">
                      {item.entities.map((e) => (
                        <span key={e}
                          className="text-[7px] font-mono px-1 py-0.5 rounded"
                          style={{ background: `${accentColor}10`, color: `${accentColor}80`, border: `1px solid ${accentColor}20` }}>
                          {e}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Data gaps */}
                  {item.dataGaps.length > 0 && (
                    <div className="flex items-start gap-1 mt-1">
                      <AlertCircle size={9} className="shrink-0 mt-0.5 text-amber-400/60" />
                      <p className="text-[8px] font-mono text-amber-400/60">
                        Gap: {item.dataGaps.join('; ')}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Fusion engine credit */}
        <p className="text-[7px] font-mono text-foreground/20 text-center pt-1">
          SPARK Signal Fusion · GDELT + USGS + NASA EONET correlation
        </p>
      </div>
    </BasePanel>
  );
};
