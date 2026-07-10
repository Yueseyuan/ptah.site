// Notary portal API — proxied through /api/notary/* to NOTARY_BACKEND_URL

export function getNotaryToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('notary_token');
}
export function getNotaryRole(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('notary_role');
}
export function setNotaryAuth(token: string, role: string) {
  localStorage.setItem('notary_token', token);
  localStorage.setItem('notary_role', role);
}
export function clearNotaryAuth() {
  localStorage.removeItem('notary_token');
  localStorage.removeItem('notary_role');
}

async function notaryFetch<T = unknown>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const token = getNotaryToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const init: RequestInit = { method, headers };
  if (body !== undefined) {
    if (body instanceof URLSearchParams) {
      init.body = body;
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
    } else {
      init.body = JSON.stringify(body);
      headers['Content-Type'] = 'application/json';
    }
  }

  const res = await fetch(path, init);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw Object.assign(new Error(err.detail || 'Request failed'), { response: { status: res.status, data: err } });
  }
  return res.json();
}

// Auth
export const notaryRegister = (data: {
  first_name: string; last_name: string; email: string; password: string;
  phone?: string; license_number?: string; license_state?: string; license_expires?: string;
}) => notaryFetch<{ id: number; email: string; access_token: string; token_type: string }>(
  'POST', '/api/notary/auth/register', data
);

export const notaryLogin = (email: string, password: string) =>
  notaryFetch<{ access_token: string; token_type: string }>(
    'POST', '/api/notary/auth/login', new URLSearchParams({ username: email, password })
  );

// Profile
export const notaryMe = () =>
  notaryFetch<{
    id: number; first_name: string; last_name: string; email: string;
    phone: string; license_number: string; license_state: string;
    license_expires: string; is_active: boolean;
  }>('GET', '/api/notary/profile/me');

// Orders
export const notaryOrders = (status?: string) =>
  notaryFetch<unknown[]>('GET', `/api/notary/orders${status ? `?status=${status}` : ''}`);

export const notaryMyOrders = () =>
  notaryFetch<unknown[]>('GET', '/api/notary/orders/mine');

export const notaryUpdateOrder = (id: number, data: Record<string, unknown>) =>
  notaryFetch('PATCH', `/api/notary/orders/${id}`, data);
