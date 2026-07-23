import { create } from 'zustand';

const getInitialUser = () => {
  try {
    const userStr = localStorage.getItem('auth_user');
    return userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    console.error("Failed to parse auth_user from localStorage, removing item.", e);
    localStorage.removeItem('auth_user');
    return null;
  }
};

export const useAuthStore = create((set) => ({
  user: getInitialUser(),
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
