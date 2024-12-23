// Environment variables in Vite use import.meta.env
export const API_BASE_URL = '/api';

export const API_ENDPOINTS = {
  convert: `${API_BASE_URL}/convert`,
  status: `${API_BASE_URL}/status`,
} as const;