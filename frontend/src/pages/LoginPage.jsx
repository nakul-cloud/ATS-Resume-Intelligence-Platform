import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../api/authApi';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { InputField } from '../components/common/InputField';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Toast } from '../components/common/Toast';

export const LoginPage = () => {
  const navigate = useNavigate();
  const loginStore = useAuthStore((state) => state.login);
  
  const [selectedRole, setSelectedRole] = useState(null); // 'candidate' | 'recruiter' | null
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleCandidateEntry = () => {
    loginStore({ name: 'Candidate User' }, 'candidate-temp-token', 'candidate');
    navigate('/candidate');
  };

  const handleRecruiterLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      triggerToast('Please provide email and password credentials.', 'warning');
      return;
    }
    
    setIsLoading(true);
    try {
      const response = await authApi.login(email, password);
      // Backend response returns { data: { access_token: "..." } } based on success_response
      const token = response.data?.access_token;
      if (token) {
        loginStore({ email }, token, 'recruiter');
        triggerToast('Authentication successful!', 'success');
        setTimeout(() => navigate('/recruiter'), 800);
      } else {
        triggerToast('Login failed: Token missing from auth response.', 'error');
      }
    } catch (err) {
      console.error(err);
      triggerToast(err.response?.data?.message || 'Invalid recruiter email or password.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface p-md">
      <div className="w-full max-w-[500px] space-y-lg">
        {/* Brand Header */}
        <div className="flex flex-col items-center justify-center text-center space-y-xs">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-container to-primary flex items-center justify-center text-white shadow-xl mb-base">
            <span className="material-symbols-outlined text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>psychology</span>
          </div>
          <h1 className="font-h2 text-h2 font-bold text-primary">Resume Intelligence</h1>
          <p className="font-body-md text-on-surface-variant">AI-Powered Resume Parsing, Evaluation, and Sourcing</p>
        </div>

        {/* Dynamic Card Container */}
        <Card variant="raised" className="relative overflow-hidden">
          {!selectedRole ? (
            /* Role Selection Screen */
            <div className="space-y-md">
              <h3 className="font-h3 text-center text-on-surface font-semibold mb-lg">Select Your Portal</h3>
              
              <div className="grid grid-cols-1 gap-md">
                <div 
                  onClick={() => setSelectedRole('candidate')}
                  className="neomorphic-inset hover:bg-surface-container-low p-md rounded-2xl border border-outline-variant flex items-center gap-md cursor-pointer hover:translate-y-[-2px] transition-all duration-200"
                >
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                    <span className="material-symbols-outlined text-2xl">person</span>
                  </div>
                  <div>
                    <h4 className="font-bold text-on-surface">Candidate Portal</h4>
                    <p className="text-xs text-outline">Upload resume, evaluate job compatibility & rewrite sections</p>
                  </div>
                </div>

                <div 
                  onClick={() => setSelectedRole('recruiter')}
                  className="neomorphic-inset hover:bg-surface-container-low p-md rounded-2xl border border-outline-variant flex items-center gap-md cursor-pointer hover:translate-y-[-2px] transition-all duration-200"
                >
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-container to-primary flex items-center justify-center text-white font-bold">
                    <span className="material-symbols-outlined text-2xl">work</span>
                  </div>
                  <div>
                    <h4 className="font-bold text-on-surface">Recruiter Sourcing Portal</h4>
                    <p className="text-xs text-outline">Index resumes, normalize job descriptions & run matches</p>
                  </div>
                </div>
              </div>
            </div>
          ) : selectedRole === 'candidate' ? (
            /* Candidate Quick Options */
            <div className="space-y-lg text-center py-md">
              <h3 className="font-h3 text-on-surface font-semibold">Candidate Portal Access</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed max-w-[360px] mx-auto">
                Evaluate your resume against target JDs, discover capability gaps, and receive suggestions in real-time.
              </p>
              
              <div className="flex flex-col gap-sm max-w-[280px] mx-auto">
                <Button variant="gradient" onClick={handleCandidateEntry}>
                  Enter Candidate View
                </Button>
                <button 
                  onClick={() => setSelectedRole(null)}
                  className="text-xs text-outline hover:text-primary transition-colors underline font-semibold focus:outline-none"
                >
                  Back to selection
                </button>
              </div>
            </div>
          ) : (
            /* Recruiter Authentication View */
            <form onSubmit={handleRecruiterLogin} className="space-y-md">
              <h3 className="font-h3 text-center text-on-surface font-semibold mb-md">Recruiter Sign In</h3>
              
              <InputField 
                label="Recruiter Email"
                placeholder="recruiter@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
              />

              <InputField 
                label="Security Password"
                placeholder="••••••••"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
              />

              <div className="flex flex-col gap-sm pt-md">
                <Button variant="gradient" type="submit" disabled={isLoading} icon="login">
                  {isLoading ? <LoadingSpinner size="sm" /> : 'Authenticate Credentials'}
                </Button>
                
                <button 
                  type="button"
                  onClick={() => setSelectedRole(null)}
                  className="text-xs text-outline hover:text-primary transition-colors underline font-semibold mt-xs focus:outline-none"
                >
                  Back to selection
                </button>
              </div>
            </form>
          )}
        </Card>

        {/* Footer info */}
        <p className="text-center text-[10px] text-outline uppercase tracking-widest font-semibold">
          Mock Recruiter Creds: recruiter@example.com / password123
        </p>
      </div>

      {toastMessage && (
        <Toast 
          message={toastMessage} 
          type={toastType} 
          onClose={() => setToastMessage(null)} 
        />
      )}
    </div>
  );
};
