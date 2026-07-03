// fetch-based API client — replaces axios to avoid browser-extension XHR interference

type FetchConfig = {
  params?: Record<string, string | number | boolean | undefined | null>;
  headers?: Record<string, string>;
  responseType?: 'blob';
};

type ApiResponse<T = unknown> = { data: T; status: number };

function buildUrl(path: string, params?: FetchConfig['params']): string {
  if (!params) return path;
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null) as [string, string | number | boolean][];
  if (!entries.length) return path;
  const qs = new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
  return `${path}?${qs}`;
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('aegis_token');
}
export function setToken(token: string) { localStorage.setItem('aegis_token', token); }
export function clearToken() { localStorage.removeItem('aegis_token'); }

async function apiFetch<T = unknown>(
  method: string,
  path: string,
  body?: unknown,
  config?: FetchConfig,
): Promise<ApiResponse<T>> {
  const url = buildUrl(path, config?.params);
  const headers: Record<string, string> = { ...(config?.headers || {}) };

  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const init: RequestInit = { method, headers };

  if (body !== undefined && body !== null) {
    if (body instanceof FormData) {
      init.body = body;
    } else if (body instanceof URLSearchParams) {
      init.body = body;
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
    } else {
      init.body = JSON.stringify(body);
      headers['Content-Type'] = 'application/json';
    }
  }

  const res = await fetch(url, init);

  if (!res.ok) {
    if (typeof window !== 'undefined') {
      const role = localStorage.getItem('aegis_role');
      if (res.status === 401 || (res.status === 403 && role === 'client')) {
        localStorage.removeItem('aegis_token');
        localStorage.removeItem('aegis_role');
        window.location.href = '/login';
      }
    }
    const err = new Error(`HTTP ${res.status}`) as Error & { response: { status: number } };
    err.response = { status: res.status };
    throw err;
  }

  const data: T = config?.responseType === 'blob'
    ? (await res.blob()) as T
    : (await res.json()) as T;

  return { data, status: res.status };
}

const api = {
  get:    <T = unknown>(path: string, config?: FetchConfig) =>
            apiFetch<T>('GET', path, undefined, config),
  post:   <T = unknown>(path: string, body?: unknown, config?: FetchConfig) =>
            apiFetch<T>('POST', path, body, config),
  put:    <T = unknown>(path: string, body?: unknown, config?: FetchConfig) =>
            apiFetch<T>('PUT', path, body, config),
  patch:  <T = unknown>(path: string, body?: unknown, config?: FetchConfig) =>
            apiFetch<T>('PATCH', path, body, config),
  delete: <T = unknown>(path: string, config?: FetchConfig) =>
            apiFetch<T>('DELETE', path, undefined, config),
};

// Clients
export const listClients = () => api.get('/api/clients/').then(r => r.data);
export const getClient = (id: number) => api.get(`/api/clients/${id}`).then(r => r.data);
export const createClient = (data: Record<string, unknown>) => api.post('/api/clients/', data).then(r => r.data);
export const updateClient = (id: number, data: Record<string, unknown>) => api.put(`/api/clients/${id}`, data).then(r => r.data);

// Cases
export const listCases = () => api.get('/api/cases/').then(r => r.data);
export const getCase = (id: number) => api.get(`/api/cases/${id}`).then(r => r.data);
export const getCaseSummary = (id: number) => api.get(`/api/cases/${id}/summary`).then(r => r.data);
export const createCase = (data: Record<string, unknown>) => api.post('/api/cases/', data).then(r => r.data);
export const updateCase = (id: number, data: Record<string, unknown>) => api.patch(`/api/cases/${id}`, data).then(r => r.data);

// Reports
export const listReports = (caseId: number) => api.get(`/api/reports/case/${caseId}`).then(r => r.data);
export const uploadReport = (formData: FormData) =>
  api.post('/api/reports/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
export const reparseReport = (reportId: number) => api.post(`/api/reports/${reportId}/reparse`).then(r => r.data);
export const deleteReport = (reportId: number) => api.delete(`/api/reports/${reportId}`);

// Tradelines
export const listTradelines = (caseId: number, bureau?: string) =>
  api.get(`/api/tradelines/case/${caseId}`, { params: bureau ? { bureau } : {} }).then(r => r.data);
export const updateTradeline = (id: number, data: Record<string, unknown>) =>
  api.patch(`/api/tradelines/${id}`, data).then(r => r.data);

// Comparison
export const listComparisons = (caseId: number) => api.get(`/api/comparison/case/${caseId}`).then(r => r.data);
export const runComparison = (caseId: number) => api.post(`/api/comparison/case/${caseId}/run`).then(r => r.data);

// Findings
export const listFindings = (caseId: number) => api.get(`/api/findings/case/${caseId}`).then(r => r.data);
export const generateFindings = (caseId: number) => api.post(`/api/findings/case/${caseId}/generate`).then(r => r.data);
export const updateFinding = (id: number, data: Record<string, unknown>) =>
  api.patch(`/api/findings/${id}`, data).then(r => r.data);

// Evidence
export const listEvidence = (caseId: number) => api.get(`/api/evidence/case/${caseId}`).then(r => r.data);
export const uploadEvidence = (caseId: number, formData: FormData) =>
  api.post(`/api/evidence/case/${caseId}/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data);
export const createEvidence = (data: Record<string, unknown>) => api.post('/api/evidence/', data).then(r => r.data);
export const deleteEvidence = (id: number) => api.delete(`/api/evidence/${id}`);

// Court Records
export const listCourtRecordsByCase = (caseId: number) => api.get(`/api/court-records/case/${caseId}`).then(r => r.data);
export const listCourtRecordsByClient = (clientId: number) => api.get(`/api/court-records/client/${clientId}`).then(r => r.data);
export const createCourtRecord = (data: Record<string, unknown>) => api.post('/api/court-records/', data).then(r => r.data);
export const deleteCourtRecord = (id: number) => api.delete(`/api/court-records/${id}`);

// Timeline
export const listTimeline = (caseId: number) => api.get(`/api/timeline/case/${caseId}`).then(r => r.data);
export const createTimelineEvent = (data: Record<string, unknown>) => api.post('/api/timeline/', data).then(r => r.data);
export const buildTimeline = (caseId: number) => api.post(`/api/timeline/case/${caseId}/build`).then(r => r.data);
export const deleteTimelineEvent = (id: number) => api.delete(`/api/timeline/${id}`);

// Strategy
export const listStrategy = (caseId: number) => api.get(`/api/strategy/case/${caseId}`).then(r => r.data);
export const generateStrategy = (caseId: number) => api.post(`/api/strategy/case/${caseId}/generate`).then(r => r.data);
export const createStrategyItem = (data: Record<string, unknown>) => api.post('/api/strategy/', data).then(r => r.data);
export const updateStrategyItem = (id: number, data: Record<string, unknown>) =>
  api.patch(`/api/strategy/${id}`, data).then(r => r.data);

// Report Generator
export const listGeneratedReports = (caseId: number) => api.get(`/api/report-generator/case/${caseId}`).then(r => r.data);
export const generateReport = (caseId: number, reportType = 'summary') =>
  api.post(`/api/report-generator/case/${caseId}/generate`, null, { params: { report_type: reportType } }).then(r => r.data);
export const downloadGeneratedReport = (reportId: number) =>
  api.get(`/api/report-generator/${reportId}/download`, { responseType: 'blob' }).then(r => r.data);
export const downloadDisputeLetter = (roundId: number) =>
  api.get(`/api/report-generator/dispute-letter/${roundId}`, { responseType: 'blob' }).then(r => r.data);
export const downloadAffidavit = (caseId: number) =>
  api.get(`/api/report-generator/affidavit/${caseId}`, { responseType: 'blob' }).then(r => r.data);
export const downloadAuthorization = (caseId: number) =>
  api.get(`/api/report-generator/authorization/${caseId}`, { responseType: 'blob' }).then(r => r.data);

// Disputes
export const listDisputeRounds = (caseId: number) => api.get(`/api/disputes/case/${caseId}`).then(r => r.data);
export const autoGenerateDisputes = (caseId: number) => api.post(`/api/disputes/case/${caseId}/auto-generate`).then(r => r.data);
export const createDisputeRound = (data: Record<string, unknown>) => api.post('/api/disputes/rounds/', data).then(r => r.data);
export const updateDisputeRound = (id: number, data: Record<string, unknown>) =>
  api.patch(`/api/disputes/rounds/${id}`, data).then(r => r.data);
export const createDisputeItem = (data: Record<string, unknown>) => api.post('/api/disputes/items/', data).then(r => r.data);
export const updateDisputeItem = (id: number, data: Record<string, unknown>) =>
  api.patch(`/api/disputes/items/${id}`, data).then(r => r.data);

// Outcomes
export const listOutcomes = (caseId: number) => api.get(`/api/outcomes/case/${caseId}`).then(r => r.data);
export const createOutcome = (data: Record<string, unknown>) => api.post('/api/outcomes/', data).then(r => r.data);
export const updateOutcome = (id: number, data: Record<string, unknown>) =>
  api.patch(`/api/outcomes/${id}`, data).then(r => r.data);
export const deleteOutcome = (id: number) => api.delete(`/api/outcomes/${id}`);

// Metro 2
export const runMetro2Analysis = (caseId: number) => api.post(`/api/metro2/case/${caseId}/analyze`).then(r => r.data);
export const listMetro2Findings = (caseId: number) => api.get(`/api/metro2/case/${caseId}`).then(r => r.data);
export const metro2FindingToDispute = (metro2FindingId: number, roundId: number, disputeReason?: string) =>
  api.post(`/api/metro2/findings/${metro2FindingId}/to-dispute`, { round_id: roundId, dispute_reason: disputeReason }).then(r => r.data);

// Learning
export const listLearning = (filters?: { bureau?: string; outcome?: string }) =>
  api.get('/api/learning/', { params: filters }).then(r => r.data);
export const createLearningEntry = (data: Record<string, unknown>) => api.post('/api/learning/', data).then(r => r.data);
export const deleteLearningEntry = (id: number) => api.delete(`/api/learning/${id}`);

// Auth
export const loginUser = (username: string, password: string) =>
  api.post('/api/auth/login', new URLSearchParams({ username, password })).then(r => r.data);
export const getMe = () => api.get('/api/auth/me').then(r => r.data);
export const updateMyProfile = (data: Record<string, unknown>) => api.patch('/api/auth/me', data).then(r => r.data);
export const registerUser = (data: Record<string, unknown>) => api.post('/api/auth/register', data).then(r => r.data);
export const listUsers = () => api.get('/api/auth/users').then(r => r.data);
export const updateUser = (id: number, data: Record<string, unknown>) => api.patch(`/api/auth/users/${id}`, data).then(r => r.data);

// Audit
export const listCaseAudit = (caseId: number) => api.get(`/api/audit/case/${caseId}`).then(r => r.data);
export const listAllAudit = () => api.get('/api/audit/').then(r => r.data);

// Portal intake (staff view)
export const listPendingPortalCases = (status = 'pending') => api.get('/api/portal/admin/pending', { params: { status } }).then(r => r.data);
export const updatePortalCaseStatus = (caseId: number, portal_status: string) =>
  api.patch(`/api/portal/admin/case/${caseId}/status`, null, { params: { portal_status } }).then(r => r.data);
export const markDocumentReviewed = (docId: number) =>
  api.patch(`/api/portal/admin/documents/${docId}/reviewed`).then(r => r.data);
export const mergeClients = (keepId: number, deleteId: number) =>
  api.post('/api/clients/admin/merge', null, { params: { keep_id: keepId, delete_id: deleteId } }).then(r => r.data);
export const deleteClientAdmin = (id: number) =>
  api.delete(`/api/clients/admin/delete/${id}`).then(r => r.data);

// Organizations
export const listOrganizations = () => api.get('/api/organizations/').then(r => r.data);
export const getOrganization = (id: number) => api.get(`/api/organizations/${id}`).then(r => r.data);
export const createOrganization = (data: Record<string, unknown>) => api.post('/api/organizations/', data).then(r => r.data);
export const updateOrganization = (id: number, data: Record<string, unknown>) => api.patch(`/api/organizations/${id}`, data).then(r => r.data);

// Inquiries
export const listInquiries = (caseId: number) => api.get(`/api/inquiries/case/${caseId}`).then(r => r.data);
export const createInquiry = (data: Record<string, unknown>) => api.post('/api/inquiries/', data).then(r => r.data);
export const deleteInquiry = (id: number) => api.delete(`/api/inquiries/${id}`);

// Personal Info
export const listPersonalInfo = (caseId: number) => api.get(`/api/personal-info/case/${caseId}`).then(r => r.data);
export const createPersonalInfo = (data: Record<string, unknown>) => api.post('/api/personal-info/', data).then(r => r.data);
export const analyzePersonalInfo = (caseId: number) => api.post(`/api/personal-info/case/${caseId}/analyze`).then(r => r.data);
export const deletePersonalInfo = (id: number) => api.delete(`/api/personal-info/${id}`);

// Inquiry Analysis
export const analyzeInquiries = (caseId: number) => api.post(`/api/inquiries/case/${caseId}/analyze`).then(r => r.data);

// Legal
export const listFederalLaws = (params?: { category?: string; search?: string }) => api.get('/api/legal/federal', { params }).then(r => r.data);
export const listAgencyGuidance = (params?: { agency?: string; search?: string }) => api.get('/api/legal/guidance', { params }).then(r => r.data);
export const listStateLaws = (params?: { state?: string; search?: string }) => api.get('/api/legal/state', { params }).then(r => r.data);
export const listCaseLaw = (params?: { topic?: string; search?: string }) => api.get('/api/legal/cases', { params }).then(r => r.data);
export const searchLegal = (q: string) => api.get('/api/legal/search', { params: { q } }).then(r => r.data);

// Legal Updates
export const listLegalUpdates = () => api.get('/api/legal-updates/').then(r => r.data);
export const submitLegalUpdate = (data: Record<string, unknown>) => api.post('/api/legal-updates/', data).then(r => r.data);
export const approveLegalUpdate = (id: number) => api.post(`/api/legal-updates/${id}/approve`).then(r => r.data);
export const rejectLegalUpdate = (id: number, notes: string) => api.post(`/api/legal-updates/${id}/reject`, { notes }).then(r => r.data);

// Applicable Laws (per case)
export const getApplicableLaws = (caseId: number) => api.get(`/api/cases/${caseId}/applicable-laws`).then(r => r.data);

// Approve Finding
export const approveFinding = (id: number, notes?: string) =>
  api.post(`/api/findings/${id}/approve`, { review_notes: notes || '' }).then(r => r.data);

// Collection Review
export const listCollectionFindings = (caseId: number) => api.get(`/api/collection-review/case/${caseId}`).then(r => r.data);
export const runCollectionAnalysis = (caseId: number) => api.post(`/api/collection-review/case/${caseId}/analyze`).then(r => r.data);

// Court Record Analysis
export const analyzeCourtRecords = (caseId: number) => api.post(`/api/court-records/case/${caseId}/analyze`).then(r => r.data);

// Analytics
export const getAnalyticsSummary = () => api.get('/api/analytics/summary').then(r => r.data);
export const getBureauAccuracy = () => api.get('/api/analytics/bureau-accuracy').then(r => r.data);
export const getDisputeOutcomes = () => api.get('/api/analytics/dispute-outcomes').then(r => r.data);
export const getFindingsTrend = () => api.get('/api/analytics/findings-trend').then(r => r.data);

// Global Search
export const globalSearch = (q: string) => api.get('/api/search/', { params: { q } }).then(r => r.data);

// Case Export
export const exportCase = (caseId: number) => api.get(`/api/cases/${caseId}/export`).then(r => r.data);

// Finding -> Dispute linking
export const addFindingToDispute = (findingId: number, roundId: number, disputeReason?: string, fcraBasis?: string) =>
  api.post('/api/disputes/add-finding', { finding_id: findingId, round_id: roundId, dispute_reason: disputeReason, fcra_basis: fcraBasis }).then(r => r.data);
export const listDisputeRoundsForCase = (caseId: number) =>
  api.get(`/api/disputes/case/${caseId}`).then(r => r.data);

// Cases by client
export const getCasesByClient = (clientId: number) =>
  api.get('/api/cases/', { params: { client_id: clientId } }).then(r => r.data);

// Tradelines CSV export
export const exportTradelinesCsv = (caseId: number) =>
  api.get(`/api/tradelines/case/${caseId}/export.csv`, { responseType: 'blob' }).then(r => r.data);

// Analyze all engines
export const analyzeAll = (caseId: number) =>
  api.post(`/api/cases/${caseId}/analyze-all`).then(r => r.data);

// AI Consultation
export const consultAI = (caseId: number, data: { finding_id?: number; user_theory: string; law_reference?: string; context?: string }) =>
  api.post(`/api/ai-consult/case/${caseId}`, data).then(r => r.data);

// Bulk update findings status
export const bulkUpdateFindings = (ids: number[], status: string) =>
  api.post('/api/findings/bulk-update', { ids, status }).then(r => r.data);

// Appointments
export const listAppointments = () => api.get('/api/appointments').then(r => r.data);
export const listUpcomingAppointments = () => api.get('/api/appointments/upcoming').then(r => r.data);
export const createAppointment = (data: Record<string, unknown>) => api.post('/api/appointments', data).then(r => r.data);
export const updateAppointment = (id: number, data: Record<string, unknown>) => api.patch(`/api/appointments/${id}`, data).then(r => r.data);
export const deleteAppointment = (id: number) => api.delete(`/api/appointments/${id}`);

// Invoices
export const listInvoices = () => api.get('/api/invoices').then(r => r.data);
export const createInvoice = (data: Record<string, unknown>) => api.post('/api/invoices', data).then(r => r.data);
export const markInvoicePaid = (id: number) => api.put(`/api/invoices/${id}/mark-paid`, {}).then(r => r.data);
export const getInvoicePdf = (id: number) => api.get(`/api/invoices/${id}/pdf`, { responseType: 'blob' }).then(r => r.data);

// Document Templates
export const listTemplates = () => api.get('/api/templates').then(r => r.data);
export const createTemplate = (data: Record<string, unknown>) => api.post('/api/templates', data).then(r => r.data);
export const updateTemplate = (id: number, data: Record<string, unknown>) => api.put(`/api/templates/${id}`, data).then(r => r.data);
export const deleteTemplate = (id: number) => api.delete(`/api/templates/${id}`);
export const seedTemplates = () => api.post('/api/templates/seed', {}).then(r => r.data);
export const previewTemplate = (id: number) => api.post(`/api/templates/${id}/preview`, {}).then(r => r.data);

export default api;
