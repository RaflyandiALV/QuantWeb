/**
 * api.js — Centralized Axios instance for QuantTrade
 *
 * Usage:
 *   import api from '../api';
 *   const res = await api.get('/api/fund/performance');
 *
 * Benefits:
 *   - Single place to update base URL
 *   - Consistent 30s timeout across all requests
 *   - Unified error logging via interceptor
 */
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  timeout: 30000,
});

// Response interceptor — logs all API errors to console for debugging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || 'unknown';
    const msg = error.response
      ? `HTTP ${error.response.status} @ ${url}`
      : `Network error @ ${url}: ${error.message}`;
    console.error('[QuantTrade API Error]', msg);
    return Promise.reject(error);
  }
);

export default api;
