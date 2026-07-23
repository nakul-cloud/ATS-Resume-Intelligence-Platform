import React from 'react';
import { Card } from '../../../components/common/Card';
import { Button } from '../../../components/common/Button';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';
import { ActiveProfileBadge } from '../../../components/common/ActiveProfileBadge';

export const TargetRoleSection = ({
  jdText,
  setJdText,
  isLoading,
  interviewState,
  clearSession,
  handleEvaluate
}) => {
  return (
    <section className="space-y-md">
      <div className="flex items-center gap-3 mb-sm">
        <span className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold font-h2">1</span>
        <h2 className="text-2xl font-bold font-h2 text-primary">Define Target Role</h2>
      </div>
      
      <Card variant="raised" className="p-lg space-y-md">
        <ActiveProfileBadge onClear={clearSession} />
        
        <div className="space-y-md">
          <div className="space-y-xs">
            <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider block font-label-caps">
              Job Description
            </label>
            <textarea 
              className="w-full px-4 py-3 rounded-xl border border-outline-variant bg-white focus:ring-1 focus:ring-primary outline-none resize-none text-xs text-on-surface leading-relaxed transition-all"
              placeholder="Paste the complete job description here for ATS analysis..."
              rows="8"
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              disabled={isLoading || interviewState === 'IN_PROGRESS'}
            />
          </div>
        </div>
      </Card>

      {interviewState === 'NOT_STARTED' && (
        <div className="flex justify-center pt-md">
          <Button 
            variant="gradient" 
            onClick={handleEvaluate}
            disabled={isLoading || !jdText.trim()}
            className="px-10 py-4 text-base font-bold rounded-full shadow-md active:scale-95"
            icon="bolt"
          >
            {isLoading ? <LoadingSpinner size="sm" /> : 'Evaluate My Fit'}
          </Button>
        </div>
      )}
    </section>
  );
};
