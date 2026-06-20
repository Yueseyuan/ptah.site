import axios from 'axios';

export const portalApi = axios.create({
  baseURL: '',
});

portalApi.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('aegis_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

portalApi.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('aegis_token');
      localStorage.removeItem('aegis_role');
      window.location.href = '/portal/login';
    }
    return Promise.reject(error);
  }
);

export function getPortalToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('aegis_token');
}

export function getPortalRole(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('aegis_role');
}

export function setPortalAuth(token: string, role: string) {
  localStorage.setItem('aegis_token', token);
  localStorage.setItem('aegis_role', role);
}

export function clearPortalAuth() {
  localStorage.removeItem('aegis_token');
  localStorage.removeItem('aegis_role');
}

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

export const portalLogin = (username: string, password: string) => {
  const form = new FormData();
  form.append('username', username);
  form.append('password', password);
  return portalApi.post('/api/auth/login', form).then(r => r.data);
};

export const portalMe = () =>
  portalApi.get('/api/portal/me').then(r => r.data);

export const portalUpdateProfile = (data: Record<string, string>) =>
  portalApi.patch('/api/portal/profile', data).then(r => r.data);

export const portalCase = () =>
  portalApi.get('/api/portal/case').then(r => r.data);

export const portalDocuments = () =>
  portalApi.get('/api/portal/documents').then(r => r.data);

export const portalUploadDocument = (formData: FormData) =>
  portalApi.post('/api/portal/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);

export const portalDisputes = () =>
  portalApi.get('/api/portal/disputes').then(r => r.data);

export const billingStatus = () =>
  portalApi.get('/api/portal/billing/status').then(r => r.data);

export const createCheckoutSession = () =>
  portalApi.post('/api/portal/billing/create-checkout').then(r => r.data);

export const createCustomerPortalSession = () =>
  portalApi.post('/api/portal/billing/customer-portal').then(r => r.data);
