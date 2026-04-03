import { apiGet, apiPost, apiPut, apiDelete } from './api';

export interface CreateTaskRequest {
  title: string;
  description?: string;
  status?: string;
  priority?: number;
  due_date?: number;
  tags?: string[];
  recurring?: string;
  meta?: Record<string, any>;
}

export interface UpdateTaskRequest {
  title?: string;
  description?: string;
  status?: string;
  priority?: number;
  due_date?: number;
  tags?: string[];
  recurring?: string;
  meta?: Record<string, any>;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: number;
  due_date?: number;
  tags: string[];
  recurring?: string;
  created_at: number;
  updated_at: number;
  meta?: Record<string, any>;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  offset: number;
  limit: number;
}

export interface TaskHistoryItem {
  id: string;
  original_task_id: string;
  status_snapshot: Record<string, any>;
  completed_at: number;
  duration_seconds?: number;
  meta?: Record<string, any>;
}

export interface TaskHistoryResponse {
  history: TaskHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateBriefingRequest {
  content_text: string;
  title?: string;
  content_audio_url?: string;
  mood?: string;
  tags?: string[];
  meta?: Record<string, any>;
}

export interface UpdateBriefingRequest {
  title?: string;
  content_text?: string;
  content_audio_url?: string;
  mood?: string;
  tags?: string[];
  meta?: Record<string, any>;
}

export interface Briefing {
  id: string;
  title: string;
  content_text: string;
  content_audio_url?: string;
  generated_at: number;
  mood: string;
  tags: string[];
  meta?: Record<string, any>;
}

export interface BriefingListResponse {
  briefings: Briefing[];
  total: number;
  offset: number;
  limit: number;
}

// Task API functions
export async function fetchTasks(filters?: {
  status?: string;
  priority?: number;
  limit?: number;
  offset?: number;
}): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.priority !== undefined) params.append('priority', String(filters.priority));
  if (filters?.limit) params.append('limit', String(filters.limit));
  if (filters?.offset) params.append('offset', String(filters.offset));

  const queryStr = params.toString();
  return apiGet<TaskListResponse>(`/personal/tasks${queryStr ? '?' + queryStr : ''}`);
}

export async function createTask(req: CreateTaskRequest): Promise<Task> {
  return apiPost<Task>('/personal/tasks', req);
}

export async function getTask(taskId: string): Promise<Task> {
  return apiGet<Task>(`/personal/tasks/${taskId}`);
}

export async function updateTask(taskId: string, req: UpdateTaskRequest): Promise<Task> {
  return apiPut<Task>(`/personal/tasks/${taskId}`, req);
}

export async function deleteTask(taskId: string): Promise<void> {
  return apiDelete<void>(`/personal/tasks/${taskId}`);
}

export async function completeTask(taskId: string): Promise<Task> {
  return apiPost<Task>(`/personal/tasks/${taskId}/complete`, {});
}

export async function fetchTaskHistory(filters?: {
  task_id?: string;
  limit?: number;
  offset?: number;
}): Promise<TaskHistoryResponse> {
  const params = new URLSearchParams();
  if (filters?.task_id) params.append('task_id', filters.task_id);
  if (filters?.limit) params.append('limit', String(filters.limit));
  if (filters?.offset) params.append('offset', String(filters.offset));

  const queryStr = params.toString();
  return apiGet<TaskHistoryResponse>(`/personal/tasks/history${queryStr ? '?' + queryStr : ''}`);
}

// Briefing API functions
export async function fetchBriefings(filters?: {
  mood?: string;
  limit?: number;
  offset?: number;
}): Promise<BriefingListResponse> {
  const params = new URLSearchParams();
  if (filters?.mood) params.append('mood', filters.mood);
  if (filters?.limit) params.append('limit', String(filters.limit));
  if (filters?.offset) params.append('offset', String(filters.offset));

  const queryStr = params.toString();
  return apiGet<BriefingListResponse>(`/personal/briefings${queryStr ? '?' + queryStr : ''}`);
}

export async function createBriefing(req: CreateBriefingRequest): Promise<Briefing> {
  return apiPost<Briefing>('/personal/briefings', req);
}

export async function getBriefing(briefingId: string): Promise<Briefing> {
  return apiGet<Briefing>(`/personal/briefings/${briefingId}`);
}

export async function getLatestBriefing(): Promise<Briefing> {
  return apiGet<Briefing>('/personal/briefings/latest');
}

export async function updateBriefing(
  briefingId: string,
  req: UpdateBriefingRequest
): Promise<Briefing> {
  return apiPut<Briefing>(`/personal/briefings/${briefingId}`, req);
}

export async function deleteBriefing(briefingId: string): Promise<void> {
  return apiDelete<void>(`/personal/briefings/${briefingId}`);
}
