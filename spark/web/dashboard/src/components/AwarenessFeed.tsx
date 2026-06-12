'use client';

export default function AwarenessFeed({ events }: { events: any[] }) {
  return (
    <div className="spark-card">
      <h2 className="text-lg font-bold spark-accent mb-4">Awareness Feed</h2>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {events.map((event, i) => (
          <div key={i} className="flex items-center gap-3 p-2 rounded bg-gray-900 text-sm">
            <span className="text-gray-500 font-mono text-xs">
              {new Date(event.timestamp * 1000).toLocaleTimeString()}
            </span>
            <span className={`px-2 py-0.5 rounded text-xs ${
              event.event_type?.includes('changed') ? 'bg-cyan-900 text-cyan-300' : 'bg-gray-800 text-gray-300'
            }`}>
              {event.event_type}
            </span>
            <span className="text-gray-400 truncate">{JSON.stringify(event.data).slice(0, 80)}</span>
          </div>
        ))}
        {events.length === 0 && <div className="text-gray-500">No awareness events yet</div>}
      </div>
    </div>
  );
}
