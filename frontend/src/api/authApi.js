import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  }
});

// Auto attach authorization token if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  login: async (username, password) => {
    // Standard OAuth2 form request structure expected by OAuth2PasswordRequestForm
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const response = await api.post('/auth/token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    return response.data;
  }
};

export const extractErrorMessage = (err, fallback = 'An unexpected error occurred.') => {
  if (!err) return fallback;
  if (err.response?.data) {
    const data = err.response.data;
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.message === 'string') return data.message;
    if (typeof data.error === 'string') return data.error;
  }
  return err.message || fallback;
};

export default api;
