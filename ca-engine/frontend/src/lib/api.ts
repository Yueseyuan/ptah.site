import axios from 'axios';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL: BASE });

// Attach JWT token from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('ca_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('ca_token');
      localStorage.removeItem('ca_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string) {
  const form = new URLSearchParams({ username: email, password });
  const { data } = await api.post('/api/auth/token', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

export async function getMe() {
  const { data } = await api.get('/api/auth/me');
  return data;
}

// ── Clients ───────────────────────────────────────────────────────────────────

export async function listClients(search?: string) {
  const { data } = await api.get('/api/clients', { params: { search } });
  return data;
}

export async function getClient(id: number) {
  const { data } = await api.get(`/api/clients/${id}`);
  return data;
}

export async function createClient(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/clients', payload);
  return data;
}

export async function updateClient(id: number, payload: Record<string, unknown>) {
  const { data } = await api.patch(`/api/clients/${id}`, payload);
  return data;
}

// ── Cases ─────────────────────────────────────────────────────────────────────

export async function listCases(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/cases', { params });
  return data;
}

export async function getCase(id: number) {
  const { data } = await api.get(`/api/cases/${id}`);
  return data;
}

export async function createCase(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/cases', payload);
  return data;
}

export async function updateCase(id: number, payload: Record<string, unknown>) {
  const { data } = await api.patch(`/api/cases/${id}`, payload);
  return data;
}

export async function analyzeCase(id: number) {
  const { data } = await api.post(`/api/cases/${id}/analyze`);
  return data;
}

// ── Documents ─────────────────────────────────────────────────────────────────

export async function listDocumentTypes() {
  const { data } = await api.get('/api/documents/types');
  return data;
}

export async function listDocuments(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/documents', { params });
  return data;
}

export async function generateDocument(caseId: number, documentType: string, extraData?: Record<string, unknown>) {
  const { data } = await api.post('/api/documents/generate', {
    case_id: caseId,
    document_type: documentType,
    extra_data: extraData,
  });
  return data;
}

export function downloadDocumentUrl(docId: number, fmt: 'docx' | 'pdf' = 'pdf') {
  return `${BASE}/api/documents/${docId}/download?fmt=${fmt}`;
}

export async function updateDocumentStatus(docId: number, status: string) {
  const { data } = await api.patch(`/api/documents/${docId}/status`, null, { params: { status } });
  return data;
}

export async function sendForSignature(docId: number, signerEmail: string, signerName: string) {
  const { data } = await api.post(`/api/documents/${docId}/send-for-signature`, null, {
    params: { signer_email: signerEmail, signer_name: signerName },
  });
  return data;
}

// ── Appointments ──────────────────────────────────────────────────────────────

export async function listAppointments(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/appointments', { params });
  return data;
}

export async function createAppointment(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/appointments', payload);
  return data;
}

export async function updateAppointment(id: number, payload: Record<string, unknown>) {
  const { data } = await api.patch(`/api/appointments/${id}`, payload);
  return data;
}

// ── Invoices ──────────────────────────────────────────────────────────────────

export async function listInvoices(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/invoices', { params });
  return data;
}

export async function createInvoice(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/invoices', payload);
  return data;
}

export async function recordPayment(invoiceId: number, amount: number, notes?: string) {
  const { data } = await api.post(`/api/invoices/${invoiceId}/payment`, { amount, notes });
  return data;
}

export function invoicePdfUrl(invoiceId: number) {
  return `${BASE}/api/invoices/${invoiceId}/pdf`;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function getDashboardStats() {
  const { data } = await api.get('/api/admin/dashboard');
  return data;
}

export async function getAuditLog(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/admin/audit-log', { params });
  return data;
}
