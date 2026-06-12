'use client';

export default function CommandCenter({ data }: { data: any }) {
  const wm = data?.working_memory || {};
  const goal = data?.current_goal;
  const obj = wm?.objective || {};
  const task = wm?.task || {};

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-3">Working Memory</h2>
        <div className="space-y-2 text-sm">
          <div><span className="text-gray-400">Objective:</span> {obj.description || 'None'}</div>
          <div><span className="text-gray-400">Progress:</span> {obj.subtasks_done || 0}/{obj.subtasks_total || 0}</div>
          <div><span className="text-gray-400">Task:</span> {task.description || 'idle'}</div>
          <div><span className="text-gray-400">Status:</span> <span className={task.status === 'running' ? 'spark-success' : ''}>{task.status || 'idle'}</span></div>
          <div><span className="text-gray-400">Window:</span> {wm?.context?.current_window || '?'}</div>
        </div>
      </div>

      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-3">Current Goal</h2>
        {goal ? (
          <div className="space-y-2 text-sm">
            <div><span className="text-gray-400">Goal:</span> {goal.description}</div>
            <div><span className="text-gray-400">Priority:</span> {goal.priority}</div>
            <div><span className="text-gray-400">Status:</span> {goal.status}</div>
          </div>
        ) : (
          <div className="text-gray-500">No active goal</div>
        )}
      </div>

      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-3">System Health</h2>
        <div className="space-y-2 text-sm">
          <div><span className="text-gray-400">CPU:</span> {data?.system_health?.cpu_percent || '?'}%</div>
          <div><span className="text-gray-400">Memory:</span> {data?.system_health?.memory_percent || '?'}%</div>
          <div><span className="text-gray-400">Platform:</span> {data?.system_health?.platform || '?'}</div>
        </div>
      </div>

      <div className="spark-card">
        <h2 className="text-lg font-bold spark-accent mb-3">Context</h2>
        <div className="space-y-2 text-sm">
          <div><span className="text-gray-400">Active Window:</span> {data?.context?.active_window || '?'}</div>
          <div><span className="text-gray-400">User Present:</span> {data?.context?.user_present ? 'Yes' : 'No'}</div>
          <div><span className="text-gray-400">Time of Day:</span> {data?.context?.time_of_day || '?'}</div>
        </div>
      </div>
    </div>
  );
}
