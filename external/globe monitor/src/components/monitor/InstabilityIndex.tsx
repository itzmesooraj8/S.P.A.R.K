/**
 * InstabilityIndex — Right floating panel.
 * Ranked list of countries with risk scores, self-drawing sparklines,
 * and click-to-flyTo map interaction.
 */
import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { countries } from '@/data/mockData';
import { BasePanel } from './BasePanel';
import { Sparkline } from './Sparkline';
import { ScrollArea } from '@/components/ui/scroll-area';

/** Risk score → text color class */
const riskTextColor = (score: number) => {
  if (score >= 80) return 'text-neon-crimson';
  if (score >= 60) return 'text-neon-amber';
  if (score >= 40) return 'text-accent';
  return 'text-neon-green';
};

/** Risk score → background color class */
const riskBgColor = (score: number) => {
  if (score >= 80) return 'bg-destructive/20';
  if (score >= 60) return 'bg-accent/20';
  if (score >= 40) return 'bg-accent/10';
  return 'bg-neon-green/10';
};

/** Risk score → sparkline stroke color */
const sparklineStroke = (score: number) => {
  if (score >= 80) return 'hsl(0, 85%, 55%)';
  if (score >= 60) return 'hsl(42, 95%, 55%)';
  if (score >= 40) return 'hsl(42, 95%, 45%)';
  return 'hsl(145, 80%, 45%)';
};

export const InstabilityIndex = () => {
  const flyTo = useMonitorStore((s) => s.flyTo);

  const sorted = useMemo(
    () => [...countries].sort((a, b) => b.riskScore - a.riskScore),
    []
  );

  return (
    <BasePanel
      title="Instability Index"
      icon={<BarChart3 size={14} className="text-neon-amber" />}
    >
      <ScrollArea className="h-[calc(100vh-200px)] max-h-[600px]">
        <div className="p-2 space-y-0.5">
          {sorted.map((country, i) => (
            <motion.button
              key={country.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                delay: i * 0.03,
                type: 'spring',
                stiffness: 300,
                damping: 25,
              }}
              onClick={() => flyTo(country.lng, country.lat, 5)}
              className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-secondary/30 transition-all group"
            >
              {/* Rank number */}
              <span className="text-[10px] font-mono text-muted-foreground w-4 text-right">
                {i + 1}
              </span>

              {/* Country name */}
              <div className="flex-1 text-left min-w-0">
                <span className="text-xs font-medium text-foreground group-hover:text-primary transition-colors truncate block">
                  {country.name}
                </span>
              </div>

              {/* Self-drawing sparkline */}
              <Sparkline
                data={country.sparklineData}
                width={60}
                height={20}
                color={sparklineStroke(country.riskScore)}
              />

              {/* Risk score badge */}
              <div
                className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold min-w-[28px] text-center ${riskTextColor(
                  country.riskScore
                )} ${riskBgColor(country.riskScore)}`}
              >
                {country.riskScore}
              </div>
            </motion.button>
          ))}
        </div>
      </ScrollArea>
    </BasePanel>
  );
};
