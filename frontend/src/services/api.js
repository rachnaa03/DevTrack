import axios from 'axios';

/**
 * Centralized Axios instance configured for the DevTrack REST API.
 * Base URL targets /api/v1 (proxied to FastAPI backend via Vite in dev).
 */
const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request Interceptor: Attach JWT Bearer Token if present in localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('devtrack_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Handle global errors (e.g., token expiration / 401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear expired local token
      localStorage.removeItem('devtrack_token');
      localStorage.removeItem('devtrack_user');
    }
    return Promise.reject(error);
  }
);

export default api;
