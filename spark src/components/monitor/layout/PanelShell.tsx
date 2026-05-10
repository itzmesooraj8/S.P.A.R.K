import React from 'react';

export function PanelShell({
  children, accentColor, width = '19rem',
}: {
  children: React.ReactNode;
  accentColor: string;
  width?: string;
}) {
  return (
    <div
      className="h-full flex flex-col rounded-xl overflow-hidden"
      style={{
        width,
        background: 'rgba(2, 8, 20, 0.82)',
        border: `1px solid ${accentColor}18`,
        backdropFilter: 'blur(28px) saturate(1.3)',
        boxShadow: `0 0 40px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04)`,
      }}
    >
      {children}
    </div>
  );
}
