// src/auth/api.js
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// api.js — replace your request interceptor with this:
// Replace the request interceptor
api.interceptors.request.use(
  (config) => {
    // Read auth token from cookie (set by LoginView as HttpOnly)
    // For non-HttpOnly fallback, also check localStorage
    const csrfToken = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1];

    if (csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }

    // Remove the localStorage token logic entirely — token is in HttpOnly cookie
    // CookieTokenAuthentication on the backend reads it automatically
    return config;
  },
  (error) => Promise.reject(error)
);

// ──────────────────────────────────────────────────────────────────────────────
//  AUTHENTIFICATION
// ──────────────────────────────────────────────────────────────────────────────
export const login = (credentials) => api.post("/auth/login/", credentials);
export const logout = () => api.post("/auth/logout/");
export const getCurrentUser = () => api.get("/auth/me/");
export const fetchMe = getCurrentUser;  // Alias pour compatibilité

// ──────────────────────────────────────────────────────────────────────────────
//  UPLOAD
// ──────────────────────────────────────────────────────────────────────────────
export const uploadFile = (file, onProgress) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/upload/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  });
};

export const getUploadStatus = () => api.get('/upload/status/');

// ──────────────────────────────────────────────────────────────────────────────
//  SCHEDULER
// ──────────────────────────────────────────────────────────────────────────────
export const runScheduler = (params) => api.post('/scheduler/run/', params);
export const getAffectations = (params) => api.get('/scheduler/affectations/', { params });
export const updateAffectation = (id, data) => api.put(`/scheduler/affectations/${id}/`, data);
export const getProfesseurs = (params) => api.get('/scheduler/professeurs/', { params });
export const getCreneaux = () => api.get('/scheduler/creneaux/');

// ──────────────────────────────────────────────────────────────────────────────
//  STATS
// ──────────────────────────────────────────────────────────────────────────────
export const getDashboard = () => api.get('/stats/dashboard/');
export const getAdminData = () => api.get('/data/');

// ──────────────────────────────────────────────────────────────────────────────
//  EXPORT
// ──────────────────────────────────────────────────────────────────────────────
export const exportExcel = () =>
  api.get('/export/excel/', { responseType: 'blob' }).then(r => {
    const url = URL.createObjectURL(r.data);
    Object.assign(document.createElement('a'), { href: url, download: 'planning_PFE.xlsx' }).click();
    URL.revokeObjectURL(url);
  });

export const exportPDF = () =>
  api.get('/export/pdf/', { responseType: 'blob' }).then(r => {
    const url = URL.createObjectURL(r.data);
    Object.assign(document.createElement('a'), { href: url, download: 'planning_PFE.pdf' }).click();
    URL.revokeObjectURL(url);
  });

// ──────────────────────────────────────────────────────────────────────────────
//  NLP STATUS
// ──────────────────────────────────────────────────────────────────────────────
export const getNlpStatus = () => api.get('/nlp/status/');

// ──────────────────────────────────────────────────────────────────────────────
//  PROFESSEUR PROFILE
// ──────────────────────────────────────────────────────────────────────────────
export const getProfesseurProfile = (profId) => api.get(`/professeur/${profId}/`);
export const updateProfesseurProfile = (profId, data) => api.put(`/professeur/${profId}/`, data);
export const getMyProfesseurProfile = () => api.get('/me/professeur/');
export const updateMyProfesseurProfile = (data) => api.put('/me/professeur/', data);
export const getMyProfesseurSpace = () => api.get('/me/professeur/espace/');

// ──────────────────────────────────────────────────────────────────────────────
//  ETUDIANT PROFILE
// ──────────────────────────────────────────────────────────────────────────────
export const getEtudiantProfile = (etudiantId) => api.get(`/etudiant/${etudiantId}/`);
export const updateEtudiantProfile = (etudiantId, data) => api.put(`/etudiant/${etudiantId}/`, data);
export const getMyEtudiantProfile = () => api.get('/me/etudiant/');
export const updateMyEtudiantProfile = (data) => api.put('/me/etudiant/', data);

export default api;