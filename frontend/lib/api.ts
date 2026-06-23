const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8083/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("apex_token");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body != null ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T = void>(path: string) => request<T>(path, { method: "DELETE" }),
};

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; token_type: string }>("/auth/login", { email, password }),
  register: (email: string, password: string) =>
    api.post<{ id: number; email: string }>("/auth/register", { email, password }),
  me: () => api.get<{ id: number; email: string; is_admin: boolean }>("/auth/me"),
};

// Agents
export const agentsApi = {
  list: () => api.get<Agent[]>("/agents"),
  create: (data: { name: string; description?: string }) => api.post<Agent>("/agents", data),
  get: (id: number) => api.get<Agent>(`/agents/${id}`),
  update: (id: number, data: Partial<Agent>) => api.patch<Agent>(`/agents/${id}`, data),
  deactivate: (id: number) => api.delete(`/agents/${id}`),
  listRuns: (id: number) => api.get<AgentRun[]>(`/agents/${id}/runs`),
  createRun: (id: number, input: Record<string, unknown>) => api.post<AgentRun>(`/agents/${id}/runs`, { input }),
};

// Memory
export const memoryApi = {
  listCollections: () => api.get<MemoryCollection[]>("/memory/collections"),
  createCollection: (name: string, description?: string) => api.post<MemoryCollection>("/memory/collections", { name, description }),
  listEntries: (params?: { q?: string; collection_id?: number }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.collection_id != null) qs.set("collection_id", String(params.collection_id));
    return api.get<MemoryEntry[]>(`/memory/entries${qs.toString() ? "?" + qs : ""}`);
  },
  createEntry: (data: { title: string; content: string; content_type?: string; collection_id?: number; importance_score?: number }) =>
    api.post<MemoryEntry>("/memory/entries", data),
  searchEntries: (q: string) => api.get<MemoryEntry[]>(`/memory/search?q=${encodeURIComponent(q)}`),
};

// Knowledge
export const knowledgeApi = {
  listNodes: (node_type?: string) => api.get<KnowledgeNode[]>(`/knowledge/nodes${node_type ? `?node_type=${node_type}` : ""}`),
  createNode: (data: { title: string; node_type?: string; content?: string; confidence_score?: number }) =>
    api.post<KnowledgeNode>("/knowledge/nodes", data),
  search: (q: string) => api.get<KnowledgeNode[]>(`/knowledge/search?q=${encodeURIComponent(q)}`),
  listEdges: (node_id?: number) => api.get<KnowledgeEdge[]>(`/knowledge/edges${node_id ? `?node_id=${node_id}` : ""}`),
  createEdge: (data: { source_node_id: number; target_node_id: number; edge_type?: string }) =>
    api.post<KnowledgeEdge>("/knowledge/edges", data),
};

// Workflows
export const workflowsApi = {
  list: () => api.get<Workflow[]>("/workflows"),
  create: (data: { name: string; description?: string }) => api.post<Workflow>("/workflows", data),
  get: (id: number) => api.get<Workflow>(`/workflows/${id}`),
  update: (id: number, data: Partial<Workflow>) => api.patch<Workflow>(`/workflows/${id}`, data),
  listSteps: (id: number) => api.get<WorkflowStep[]>(`/workflows/${id}/steps`),
  addStep: (id: number, data: { name: string; step_type: string; order_index: number }) =>
    api.post<WorkflowStep>(`/workflows/${id}/steps`, data),
  listRuns: (id: number) => api.get<WorkflowRun[]>(`/workflows/${id}/runs`),
  createRun: (id: number, input?: Record<string, unknown>) => api.post<WorkflowRun>(`/workflows/${id}/runs`, { input }),
};

// Repo Reviews
export const reviewsApi = {
  list: (params?: { status?: string }) => {
    const qs = params?.status ? `?status=${params.status}` : "";
    return api.get<RepoReview[]>(`/repo-reviews${qs}`);
  },
  create: (data: { repo_url: string; repo_name: string; branch?: string }) =>
    api.post<RepoReview>("/repo-reviews", data),
  get: (id: number) => api.get<RepoReview>(`/repo-reviews/${id}`),
  updateStatus: (id: number, data: { status: string; classification?: string; overall_score?: number }) =>
    api.patch<RepoReview>(`/repo-reviews/${id}/status`, data),
  listStages: (id: number) => api.get<ReviewStage[]>(`/repo-reviews/${id}/stages`),
  getReport: (id: number) => api.get<ReviewReport>(`/repo-reviews/${id}/report`),
};

// Models
export const modelsApi = {
  listProviders: () => api.get<Provider[]>("/models/providers"),
  listModels: () => api.get<ModelInfo[]>("/models"),
};

// Chief
export const chiefApi = {
  run: (goal: string) => api.post<ChiefRunResult>("/chief/run", { goal }),
  listRuns: () => api.get<ChiefRunSummary[]>("/chief/runs"),
  getRun: (id: number) => api.get<ChiefRunSummary>(`/chief/runs/${id}`),
};

// Types
export interface Agent {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentRun {
  id: number;
  agent_id: number;
  status: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  created_at: string;
}

export interface MemoryCollection {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface MemoryEntry {
  id: number;
  collection_id: number | null;
  title: string;
  content: string;
  content_type: string;
  importance_score: number;
  is_active: boolean;
  created_at: string;
}

export interface KnowledgeNode {
  id: number;
  title: string;
  node_type: string;
  content: string | null;
  confidence_score: number;
  is_active: boolean;
  created_at: string;
}

export interface KnowledgeEdge {
  id: number;
  source_node_id: number;
  target_node_id: number;
  edge_type: string;
  weight: number;
  label: string | null;
  created_at: string;
}

export interface Workflow {
  id: number;
  name: string;
  description: string | null;
  status: string;
  is_active: boolean;
  created_at: string;
}

export interface WorkflowStep {
  id: number;
  workflow_id: number;
  name: string;
  step_type: string;
  order_index: number;
  is_active: boolean;
}

export interface WorkflowRun {
  id: number;
  workflow_id: number;
  status: string;
  input: Record<string, unknown> | null;
  created_at: string;
}

export interface RepoReview {
  id: number;
  repo_url: string;
  repo_name: string;
  branch: string;
  status: string;
  classification: string | null;
  overall_score: number | null;
  summary: string | null;
  created_at: string;
}

export interface ReviewStage {
  id: number;
  review_id: number;
  stage_type: string;
  verdict: string;
  score: number | null;
  notes: string | null;
  created_at: string;
}

export interface ReviewReport {
  id: number;
  review_id: number;
  classification: string;
  overall_score: number;
  executive_summary: string | null;
  stage_scores: Record<string, number>;
  recommendations: string[] | null;
  blockers: string[] | null;
  content: string | null;
  created_at: string;
}

export interface Provider {
  name: string;
  healthy: boolean;
  model_count: number;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_length: number;
}

export interface ChiefSubtask {
  title: string;
  description: string;
  agent_name: string;
  agent_run_id: number | null;
  output: string | null;
}

export interface ChiefRunResult {
  run_id: number | null;
  subtasks: ChiefSubtask[];
  merged_output: string | null;
  error: string | null;
}

export interface ChiefRunSummary {
  id: number;
  name: string;
  status: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}
