import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.message, error.response?.status);
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (email, password, fullName, orgId) =>
    api.post('/register', { email, password, full_name: fullName, org_id: orgId }),
  login: (email, password) =>
    api.post('/login', { email, password }),
  getCurrentUser: () =>
    api.get('/me'),
};

export const orgAPI = {
  create: (name, domain, revenue, size) =>
    api.post('/orgs', { name, domain, revenue, size }),
  getOrg: (orgId) =>
    api.get(`/orgs/${orgId}`),
};

export const reportAPI = {
  upload: (file, category) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  listReports: () =>
    api.get('/reports'),
  getReport: (reportId) =>
    api.get(`/reports/${reportId}`),
  getReportStatus: (reportId) =>
    api.get(`/reports/${reportId}/status`),
  createPaymentSession: (reportId, amount) =>
    api.post('/payment/checkout', { report_id: reportId, amount }),
  download: (reportId) =>
    api.get(`/download/${reportId}`, { responseType: 'blob' }),
  downloadFullReport: (reportId) =>
    api.get(`/download/${reportId}/full-report`, { responseType: 'blob' }),
  markPaid: (reportId) =>
    api.post(`/reports/${reportId}/mark-paid`),
  generateBenchmark: (reportId) =>
    api.post(`/reports/${reportId}/benchmark`),
  getBenchmark: (reportId) =>
    api.get(`/reports/${reportId}/benchmark`),
};

export default api;
