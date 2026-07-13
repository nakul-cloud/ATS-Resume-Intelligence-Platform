import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { useCandidateStore } from '../../store/candidateStore';

export const TopNavBar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { role, user, logout } = useAuthStore();
  const { clearSession } = useCandidateStore();

  const handleRoleSwitch = (newRole) => {
    if (newRole === 'recruiter' && role !== 'recruiter') {
      navigate('/');
    } else if (newRole === 'candidate' && role !== 'candidate') {
      navigate('/candidate');
    }
  };

  const handleLogout = () => {
    logout();
    clearSession();
    navigate('/');
  };

  return (
    <nav className="bg-surface/95 backdrop-blur-md sticky top-0 z-50 border-b border-outline-variant shadow-sm w-full">
      <div className="max-w-container-max mx-auto px-md py-sm flex justify-between items-center">
        <div className="flex items-center gap-base cursor-pointer" onClick={() => navigate(role === 'recruiter' ? '/recruiter' : '/candidate')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-container to-primary flex items-center justify-center text-white shadow-lg">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>psychology</span>
          </div>
          <h1 className="font-h3 text-h3 font-bold text-primary">Resume Intelligence</h1>
          {role === 'recruiter' && (
            <span className="bg-primary/10 text-primary px-3 py-1 rounded-full font-label-caps text-label-caps border border-primary/20">RECRUITER</span>
          )}
        </div>
        
        <div className="flex items-center gap-md">
          {role && (
            <div className="flex bg-surface-container-high p-1 rounded-full border border-outline-variant shadow-inner">
              <button 
                onClick={() => handleRoleSwitch('candidate')}
                className={`flex items-center px-4 py-1.5 rounded-full text-label-caps font-label-caps transition-all duration-200 ${
                  role === 'candidate' 
                    ? 'bg-primary text-on-primary shadow-sm font-bold scale-[1.02]' 
                    : 'text-on-surface-variant hover:bg-surface-variant/40 hover:text-primary'
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                Candidate Mode
              </button>
              <button 
                onClick={() => handleRoleSwitch('recruiter')}
                className={`flex items-center px-4 py-1.5 rounded-full text-label-caps font-label-caps transition-all duration-200 ${
                  role === 'recruiter' 
                    ? 'bg-primary text-on-primary shadow-sm font-bold scale-[1.02]' 
                    : 'text-on-surface-variant hover:bg-surface-variant/40 hover:text-primary'
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5">
                  <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
                </svg>
                Recruiter Mode
              </button>
            </div>
          )}

          {user && (
            <div className="flex items-center gap-sm">
              <div className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center border border-outline-variant text-secondary text-sm">
                <span className="material-symbols-outlined text-sm">person</span>
              </div>
              <button 
                onClick={handleLogout}
                className="flex items-center text-xs text-on-surface-variant hover:text-primary transition-colors font-semibold"
              >
                Sign Out
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="ml-1.5 opacity-80 hover:opacity-100">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
