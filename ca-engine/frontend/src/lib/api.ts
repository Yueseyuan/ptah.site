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

api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
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

// ── Division 1 — Notary Jobs ──────────────────────────────────────────────────

export async function listNotaryJobs(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/notary-jobs', { params });
  return data;
}

export async function createNotaryJob(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/notary-jobs', payload);
  return data;
}

export async function getNotaryJob(id: number) {
  const { data } = await api.get(`/api/notary-jobs/${id}`);
  return data;
}

export async function updateNotaryJobStatus(id: number, status: string) {
  const { data } = await api.patch(`/api/notary-jobs/${id}/status`, { status });
  return data;
}

// ── Division 2 — Credit Restoration ──────────────────────────────────────────

export async function listCreditCases(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/credit/cases', { params });
  return data;
}

export async function createCreditCase(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/credit/cases', payload);
  return data;
}

export async function getCreditCase(id: number) {
  const { data } = await api.get(`/api/credit/cases/${id}`);
  return data;
}

export async function addDisputeItem(caseId: number, payload: Record<string, unknown>) {
  const { data } = await api.post(`/api/credit/cases/${caseId}/disputes`, payload);
  return data;
}

export async function updateDisputeItem(itemId: number, payload: Record<string, unknown>) {
  const { data } = await api.patch(`/api/credit/disputes/${itemId}`, payload);
  return data;
}

// ── Division 3 — Criminal Relief ─────────────────────────────────────────────

export async function listReliefCases(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/relief/cases', { params });
  return data;
}

export async function createReliefCase(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/relief/cases', payload);
  return data;
}

export async function getReliefCase(id: number) {
  const { data } = await api.get(`/api/relief/cases/${id}`);
  return data;
}

export async function addCriminalRecord(caseId: number, payload: Record<string, unknown>) {
  const { data } = await api.post(`/api/relief/cases/${caseId}/records`, payload);
  return data;
}

// ── Division 4 — Document Prep ────────────────────────────────────────────────

export async function listDocPrepOrders(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/docprep/orders', { params });
  return data;
}

export async function createDocPrepOrder(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/docprep/orders', payload);
  return data;
}

export async function getDocPrepOrder(id: number) {
  const { data } = await api.get(`/api/docprep/orders/${id}`);
  return data;
}

export async function createHKPInstrument(orderId: number, payload: Record<string, unknown>) {
  const { data } = await api.post(`/api/docprep/orders/${orderId}/hkp`, payload);
  return data;
}

// ── Division 5 — Asset Recovery ───────────────────────────────────────────────

export async function listRecoveryCases(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/recovery/cases', { params });
  return data;
}

export async function createRecoveryCase(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/recovery/cases', payload);
  return data;
}

export async function getRecoveryCase(id: number) {
  const { data } = await api.get(`/api/recovery/cases/${id}`);
  return data;
}

export async function addRecoveryAsset(caseId: number, payload: Record<string, unknown>) {
  const { data } = await api.post(`/api/recovery/cases/${caseId}/assets`, payload);
  return data;
}

export async function recordRecoveredFunds(caseId: number, assetId: number, recoveredAmount: number) {
  const { data } = await api.post(`/api/recovery/cases/${caseId}/record-funds`, {
    asset_id: assetId,
    recovered_amount: recoveredAmount,
  });
  return data;
}

// ── Division 6 — Business Consulting ─────────────────────────────────────────

export async function listConsultingEngagements(params?: Record<string, unknown>) {
  const { data } = await api.get('/api/consulting/engagements', { params });
  return data;
}

export async function createConsultingEngagement(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/consulting/engagements', payload);
  return data;
}

export async function getConsultingEngagement(id: number) {
  const { data } = await api.get(`/api/consulting/engagements/${id}`);
  return data;
}

export async function updateConsultingSessionNotes(id: number, payload: Record<string, unknown>) {
  const { data } = await api.patch(`/api/consulting/engagements/${id}/notes`, payload);
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
