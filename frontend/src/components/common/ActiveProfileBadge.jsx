import React from 'react';
import { useCandidateStore } from '../../store/candidateStore';

export const ActiveProfileBadge = ({ onClear }) => {
  const { parsedProfile, candidateId } = useCandidateStore();

  if (!parsedProfile) return null;

  const name = parsedProfile.name || 'Candidate';
  const labelText = name;

  return (
    <div className="flex items-center justify-between bg-primary/5 p-sm rounded-xl border border-primary/20 backdrop-blur-sm animate-fade-in w-full">
      <div className="flex items-center">
        <div className="w-10 h-10 rounded-full bg-primary-fixed overflow-hidden flex-shrink-0 flex items-center justify-center text-primary font-bold mr-3 border border-outline-variant/30">
          <span className="material-symbols-outlined">person</span>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-outline block font-label-caps font-semibold">Active Profile</div>
          <div className="text-sm font-semibold text-on-surface">{labelText}</div>
        </div>
      </div>
      {onClear && (
        <button 
          onClick={onClear} 
          className="text-xs text-primary hover:text-primary-container underline font-semibold focus:outline-none"
        >
          Change Profile
        </button>
      )}
    </div>
  );
};
