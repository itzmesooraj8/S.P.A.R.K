import React, { useState } from 'react';
import { useTaskStore, Task } from '../store/useTaskStore';
import { createTask, updateTask, deleteTask, completeTask } from '../lib/tasks';
import './TaskPanel.css';

export const TaskPanel: React.FC = () => {
  const { tasks, addTask, updateTask: updateTaskStore, removeTask } = useTaskStore();
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [expandedStatus, setExpandedStatus] = useState<string>('PENDING');
  const [isAdding, setIsAdding] = useState(false);

  const handleCreateTask = async () => {
    if (!newTaskTitle.trim()) return;

    setIsAdding(true);
    try {
      const newTask = await createTask({
        title: newTaskTitle,
        status: 'PENDING',
        priority: 1,
      });
      addTask(newTask);
      setNewTaskTitle('');
    } catch (err) {
      console.error('Failed to create task:', err);
      alert('Failed to create task');
    } finally {
      setIsAdding(false);
    }
  };

  const handleCompleteTask = async (task: Task) => {
    try {
      const updated = await completeTask(task.id);
      updateTaskStore(task.id, updated);
    } catch (err) {
      console.error('Failed to complete task:', err);
      alert('Failed to complete task');
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm('Delete this task?')) return;

    try {
      await deleteTask(taskId);
      removeTask(taskId);
    } catch (err) {
      console.error('Failed to delete task:', err);
      alert('Failed to delete task');
    }
  };

  const statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED'];
  const priorityColors: Record<number, string> = {
    0: '#9CA3AF',
    1: '#3B82F6',
    2: '#F59E0B',
    3: '#EF4444',
  };

  const groupedTasks = statuses.reduce(
    (acc, status) => {
      acc[status] = tasks.filter((t) => t.status === status);
      return acc;
    },
    {} as Record<string, Task[]>
  );

  return (
    <div className="task-panel">
      <div className="task-panel-header">
        <h2>📋 Tasks</h2>
        <span className="task-count">{tasks.filter((t) => t.status !== 'COMPLETED').length}</span>
      </div>

      <div className="task-quick-add">
        <input
          type="text"
          placeholder="Add new task..."
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleCreateTask()}
          disabled={isAdding}
        />
        <button onClick={handleCreateTask} disabled={isAdding || !newTaskTitle.trim()}>
          {isAdding ? '⟳' : '+'}
        </button>
      </div>

      <div className="task-sections">
        {statuses.map((status) => (
          <div key={status} className="task-section">
            <div
              className="task-section-header"
              onClick={() =>
                setExpandedStatus(expandedStatus === status ? '' : status)
              }
            >
              <span className="section-title">
                {expandedStatus === status ? '▼' : '▶'} {status}
              </span>
              <span className="section-count">{groupedTasks[status].length}</span>
            </div>

            {expandedStatus === status && (
              <div className="task-list">
                {groupedTasks[status].length === 0 ? (
                  <div className="task-empty">No tasks</div>
                ) : (
                  groupedTasks[status].map((task) => (
                    <div key={task.id} className="task-item">
                      <div className="task-info">
                        <div className="task-title-row">
                          <span
                            className="priority-badge"
                            style={{
                              backgroundColor: priorityColors[task.priority] || '#6B7280',
                            }}
                          />
                          <span className="task-title">{task.title}</span>
                        </div>
                        {task.description && (
                          <p className="task-description">{task.description}</p>
                        )}
                        {task.tags.length > 0 && (
                          <div className="task-tags">
                            {task.tags.map((tag) => (
                              <span key={tag} className="tag">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="task-actions">
                        {status !== 'COMPLETED' && (
                          <button
                            className="btn-complete"
                            onClick={() => handleCompleteTask(task)}
                            title="Mark complete"
                          >
                            ✓
                          </button>
                        )}
                        <button
                          className="btn-delete"
                          onClick={() => handleDeleteTask(task.id)}
                          title="Delete"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TaskPanel;
