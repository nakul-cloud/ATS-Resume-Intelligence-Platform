import React from 'react';
import { useCandidateStore } from '../../store/candidateStore';

export const SubNavPills = ({ activeTab, onTabChange }) => {
  const { parsedProfile } = useCandidateStore();

  const tabs = [
    { id: 'upload', label: 'Upload Resume', disabled: false },
    { id: 'evaluate', label: 'Self Evaluation', disabled: !parsedProfile },
    { id: 'projects', label: 'Projects', disabled: !parsedProfile },
    { id: 'rewrite', label: 'Rewrite Resume', disabled: !parsedProfile },
  ];

  return (
    <div className="w-full flex justify-center py-base bg-surface-container-lowest/50 sticky top-[72px] z-40">
      <div className="flex gap-base bg-surface-container rounded-full p-1.5 border border-outline-variant neomorphic-raised">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            disabled={tab.disabled}
            onClick={() => onTabChange(tab.id)}
            className={`px-6 py-2 rounded-full font-label-caps text-label-caps transition-all duration-300 ${
              tab.disabled 
                ? 'opacity-50 cursor-not-allowed text-on-surface-variant' 
                : activeTab === tab.id
                  ? 'active-pill font-bold'
                  : 'text-on-surface-variant hover:bg-secondary-container'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
};
