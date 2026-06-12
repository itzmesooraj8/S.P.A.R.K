'use client';

export default function WorldModel({ model, context }: { model: any; context: any }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-4">World Model</h2>
        <div className="space-y-3">
          <div className="p-3 rounded bg-gray-900">
            <div className="text-sm text-gray-400">Current Activity</div>
            <div className="text-lg font-bold spark-accent">{model?.current_activity || 'unknown'}</div>
          </div>
          <div className="p-3 rounded bg-gray-900">
            <div className="text-sm text-gray-400 mb-2">Predicted Needs</div>
            {model?.predictions?.map((p: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="spark-success">{(p.confidence * 100).toFixed(0)}%</span>
                <span>{p.need}</span>
                <span className="text-gray-500 text-xs">{p.reason}</span>
              </div>
            ))}
            {(!model?.predictions || model.predictions.length === 0) && (
              <div className="text-gray-500 text-sm">No predictions</div>
            )}
          </div>
        </div>
      </div>

      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-4">User Habits</h2>
        <div className="space-y-2">
          {Object.entries(model?.habits?.frequent_apps || {}).map(([app, count]: [string, any]) => (
            <div key={app} className="flex justify-between p-2 rounded bg-gray-900 text-sm">
              <span>{app}</span>
              <span className="spark-accent">{count}x</span>
            </div>
          ))}
          {Object.keys(model?.habits?.frequent_apps || {}).length === 0 && (
            <div className="text-gray-500">No habits tracked yet</div>
          )}
        </div>
      </div>

      <div className="spark-card lg:col-span-2">
        <h2 className="text-lg font-bold spark-accent mb-4">Activity Patterns</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(model?.patterns || {}).map(([name, pattern]: [string, any]) => (
            <div key={name} className="p-3 rounded bg-gray-900">
              <div className="font-bold text-sm">{name}</div>
              <div className="text-xs text-gray-400">Confidence: {((pattern.confidence || 0) * 100).toFixed(0)}%</div>
              <div className="text-xs text-gray-400">Seen: {pattern.occurrences || 0}x</div>
              <div className="mt-1 h-1 bg-gray-800 rounded overflow-hidden">
                <div className="h-full bg-cyan-500 rounded" style={{ width: `${(pattern.confidence || 0) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
