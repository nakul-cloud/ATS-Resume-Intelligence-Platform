import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { LoginPage } from '../pages/LoginPage';
import { CandidateDashboard } from '../pages/candidate/CandidateDashboard';
import { RecruiterDashboard } from '../pages/recruiter/RecruiterDashboard';

// Route guard for Candidates
const CandidateRoute = ({ children }) => {
  const { role } = useAuthStore();
  if (role !== 'candidate') {
    return <Navigate to="/" replace />;
  }
  return children;
};

// Route guard for Recruiters (checks for JWT token)
const RecruiterRoute = ({ children }) => {
  const { role, token } = useAuthStore();
  if (role !== 'recruiter' || !token) {
    return <Navigate to="/" replace />;
  }
  return children;
};

export const AppRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Login Selector */}
        <Route path="/" element={<LoginPage />} />

        {/* Candidate Portal */}
        <Route 
          path="/candidate" 
          element={
            <CandidateRoute>
              <CandidateDashboard />
            </CandidateRoute>
          } 
        />

        {/* Recruiter Portal */}
        <Route 
          path="/recruiter/*" 
          element={
            <RecruiterRoute>
              <RecruiterDashboard />
            </RecruiterRoute>
          } 
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
