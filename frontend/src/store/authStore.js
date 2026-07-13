import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: localStorage.getItem('auth_user') ? JSON.parse(localStorage.getItem('auth_user')) : null,
  token: localStorage.getItem('auth_token') || null,
  role: localStorage.getItem('auth_role') || null, // 'candidate' or 'recruiter'
  
  login: (userData, token, role) => {
    localStorage.setItem('auth_user', JSON.stringify(userData));
    localStorage.setItem('auth_token', token);
    localStorage.setItem('auth_role', role);
    set({ user: userData, token, role });
  },
  
  logout: () => {
    localStorage.removeItem('auth_user');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_role');
    localStorage.removeItem('active_candidate_profile');
    localStorage.removeItem('current_candidate_id');
    set({ user: null, token: null, role: null });
  }
}));
