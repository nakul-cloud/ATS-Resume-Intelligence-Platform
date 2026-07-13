import React, { useState } from 'react';
import { TopNavBar } from '../../components/layout/TopNavBar';
import { SubNavPills } from '../../components/layout/SubNavPills';
import { Footer } from '../../components/layout/Footer';
import { UploadTab } from './UploadTab';
import { EvaluationTab } from './EvaluationTab';
import { ProjectsTab } from './ProjectsTab';
import { RewriteTab } from './RewriteTab';

export const CandidateDashboard = () => {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'evaluate' | 'projects' | 'rewrite'

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'upload':
        return <UploadTab onTabChange={setActiveTab} />;
      case 'evaluate':
        return <EvaluationTab />;
      case 'projects':
        return <ProjectsTab />;
      case 'rewrite':
        return <RewriteTab />;
      default:
        return <UploadTab onTabChange={setActiveTab} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface text-on-surface">
      <TopNavBar />
      <SubNavPills activeTab={activeTab} onTabChange={setActiveTab} />
      
      <main className="max-w-container-max mx-auto w-full px-lg py-lg flex-1">
        {renderActiveTab()}
      </main>
      
      <Footer />
    </div>
  );
};
