import React from 'react';
import { Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { TopNavBar } from '../../components/layout/TopNavBar';
import { Footer } from '../../components/layout/Footer';
import { MetricsPage } from './MetricsPage';
import { CandidateSearchPage } from './CandidateSearchPage';
import { CandidateUploadPage } from './CandidateUploadPage';

export const RecruiterDashboard = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  const navLinks = [
    { path: '/recruiter/upload', label: 'Upload Resume', icon: 'upload_file' },
    { path: '/recruiter/candidates', label: 'Candidate Matcher', icon: 'groups' },
    { path: '/recruiter/metrics', label: 'Metrics', icon: 'analytics' }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-surface text-on-surface">
      <TopNavBar />
      
      {/* Recruiter Navigation Header */}
      <div className="w-full flex justify-center py-base bg-surface-container-lowest/50 border-b border-outline-variant/30 sticky top-[72px] z-40">
        <div className="flex gap-base bg-surface-container rounded-full p-1.5 border border-outline-variant neomorphic-raised">
          {navLinks.map((link) => {
            const isActive = currentPath === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`px-6 py-2 rounded-full font-label-caps text-label-caps transition-all duration-300 flex items-center gap-xs ${
                  isActive
                    ? 'active-pill font-bold'
                    : 'text-on-surface-variant hover:bg-secondary-container'
                }`}
              >
                <span className="material-symbols-outlined text-sm">{link.icon}</span>
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>

      <main className="max-w-container-max mx-auto w-full px-lg py-lg flex-1">
        <Routes>
          <Route path="upload" element={<CandidateUploadPage />} />
          <Route path="metrics" element={<MetricsPage />} />
          <Route path="candidates" element={<CandidateSearchPage />} />
          <Route path="*" element={<Navigate to="upload" replace />} />
        </Routes>
      </main>

      <Footer />
    </div>
  );
};
