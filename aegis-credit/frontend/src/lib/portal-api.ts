// fetch-based portal API client — mirrors admin api.ts approach

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
  return `${path}?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()}`;
}

export function getPortalToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('portal_token');
}
export function getPortalRole(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('portal_role');
}
export function setPortalAuth(token: string, role: string) {
  localStorage.setItem('portal_token', token);
  localStorage.setItem('portal_role', role);
}
export function clearPortalAuth() {
  localStorage.removeItem('portal_token');
  localStorage.removeItem('portal_role');
}

async function portalFetch<T = unknown>(
  method: string,
  path: string,
  body?: unknown,
  config?: FetchConfig,
): Promise<ApiResponse<T>> {
  const url = buildUrl(path, config?.params);
  const headers: Record<string, string> = { ...(config?.headers || {}) };

  const token = getPortalToken();
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
    if (res.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('portal_token');
      localStorage.removeItem('portal_role');
      window.location.href = '/portal/login';
    }
    const err = new Error(`HTTP ${res.status}`) as Error & { response: { status: number; data?: unknown } };
    let errData: unknown;
    try { errData = await res.json(); } catch { /* ignore */ }
    err.response = { status: res.status, data: errData };
    throw err;
  }

  const data: T = config?.responseType === 'blob'
    ? (await res.blob()) as T
    : (await res.json()) as T;
  return { data, status: res.status };
}

export const portalApi = {
  get:    <T = unknown>(path: string, config?: FetchConfig) =>
            portalFetch<T>('GET', path, undefined, config),
  post:   <T = unknown>(path: string, body?: unknown, config?: FetchConfig) =>
            portalFetch<T>('POST', path, body, config),
  patch:  <T = unknown>(path: string, body?: unknown, config?: FetchConfig) =>
            portalFetch<T>('PATCH', path, body, config),
  delete: <T = unknown>(path: string, config?: FetchConfig) =>
            portalFetch<T>('DELETE', path, undefined, config),
};

export interface RegisterData {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  dob?: string;
  ssn_last4?: string;
  username: string;
  password: string;
}

export const portalRegister = (data: RegisterData) =>
  portalApi.post('/api/portal/register', data).then(r => r.data);

export const portalLogin = (username: string, password: string) =>
  portalApi.post('/api/auth/login', new URLSearchParams({ username, password })).then(r => r.data);

export const portalMe = () =>
  portalApi.get('/api/portal/me').then(r => r.data);

export const portalUpdateProfile = (data: Record<string, string>) =>
  portalApi.patch('/api/portal/profile', data).then(r => r.data);

export const portalCase = () =>
  portalApi.get('/api/portal/case').then(r => r.data);

export const portalDocuments = () =>
  portalApi.get('/api/portal/documents').then(r => r.data);

export const portalUploadDocument = async (formData: FormData) => {
  const token = getPortalToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch('/api/portal/documents/upload', { method: 'POST', headers, body: formData });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};

export const portalDisputes = () =>
  portalApi.get('/api/portal/disputes').then(r => r.data);

export const portalOutcomes = () =>
  portalApi.get('/api/portal/outcomes').then(r => r.data);

export const billingStatus = () =>
  portalApi.get('/api/portal/billing/status').then(r => r.data);

export const forgotPassword = (email: string) =>
  portalApi.post('/api/portal/forgot-password', { email }).then(r => r.data);

export const resetPassword = (token: string, new_password: string) =>
  portalApi.post('/api/portal/reset-password', { token, new_password }).then(r => r.data);

export const createCheckoutSession = () =>
  portalApi.post('/api/portal/billing/create-checkout').then(r => r.data);

export const createCustomerPortalSession = () =>
  portalApi.post('/api/portal/billing/customer-portal').then(r => r.data);
