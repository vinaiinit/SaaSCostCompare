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
  forgotPassword: (email) =>
    api.post('/forgot-password', { email }),
  resetPassword: (token, newPassword) =>
    api.post('/reset-password', { token, new_password: newPassword }),
};

export const orgAPI = {
  create: (name, industry, revenue, size) =>
    api.post('/orgs', { name, industry, revenue, size }),
  getOrg: (orgId) =>
    api.get(`/orgs/${orgId}`),
};

export const reportAPI = {
  upload: (files, category) => {
    const formData = new FormData();
    const fileArray = Array.isArray(files) ? files : [files];
    fileArray.forEach((file) => formData.append('files', file));
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
  getLineItems: (uploadId) =>
    api.get(`/uploads/${uploadId}/line-items`),
  updateLineItem: (uploadId, itemId, data) =>
    api.put(`/uploads/${uploadId}/line-items/${itemId}`, data),
  checkFeasibility: (uploadId) =>
    api.post(`/uploads/${uploadId}/feasibility`),
  runComparison: (uploadId) =>
    api.post(`/uploads/${uploadId}/compare`),
  getComparison: (uploadId) =>
    api.get(`/uploads/${uploadId}/comparison`),
  generateBenchmark: (reportId) =>
    api.post(`/reports/${reportId}/benchmark`),
  getBenchmark: (reportId) =>
    api.get(`/reports/${reportId}/benchmark`),
  downloadFullReport: (reportId) =>
    api.get(`/download/${reportId}/full-report`, { responseType: 'blob' }),
  createPaymentSession: (reportId, amount) =>
    api.post('/payment/checkout', { report_id: reportId, amount }),
};

export const coverageAPI = {
  getAll: () =>
    api.get('/data-coverage'),
  getVendor: (vendorName) =>
    api.get(`/data-coverage/${vendorName}`),
};

export const campaignAPI = {
  submit: (files, vendorName, email, companyName, industry, companySize) => {
    const formData = new FormData();
    const fileArray = Array.isArray(files) ? files : [files];
    fileArray.forEach((file) => formData.append('files', file));
    formData.append('vendor_name', vendorName);
    if (email) formData.append('email', email);
    if (companyName) formData.append('company_name', companyName);
    if (industry) formData.append('industry', industry);
    if (companySize) formData.append('company_size', companySize);
    return api.post('/campaign/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getStatus: (submissionId) =>
    api.get(`/campaign/status/${submissionId}`),
};

export const contactAPI = {
  submit: (name, email, company, message) =>
    api.post('/contact', { name, email, company, message }),
};

export const licenseAPI = {
  analyze: (vendorName, credentials) =>
    api.post('/license-analysis', { vendor_name: vendorName, credentials }),
  list: () =>
    api.get('/license-analysis'),
  get: (analysisId) =>
    api.get(`/license-analysis/${analysisId}`),
};

export default api;
