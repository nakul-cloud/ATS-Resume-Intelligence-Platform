import React from 'react';
import { Card } from '../../../components/common/Card';
import { Button } from '../../../components/common/Button';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';

export const AnalysisResultsDashboard = ({
  evaluationResult,
  scoreTier,
  TIER_CONFIG,
  interviewState,
  handleStartInterview,
  isStartingInterview,
  setShowAllStrengths,
  setShowAllGaps
}) => {
  if (!evaluationResult) return null;

  return (
    <section className="space-y-md animate-fade-in">
      <div className="flex items-center gap-3 mb-sm">
        <span className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold font-h2">2</span>
        <h2 className="text-2xl font-bold font-h2 text-primary">AI Analysis Results</h2>
      </div>
      
      <Card variant="raised" className="overflow-hidden p-0 border border-outline-variant/30">
        {/* Result Banner */}
        <div className="bg-primary/5 border-b border-outline-variant/30 py-5 px-lg flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-primary text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>verified</span>
            <h3 className="text-lg font-bold text-on-surface font-h3">
              {evaluationResult.score_100 >= 80 ? 'Strong Match!' : evaluationResult.score_100 >= 60 ? 'Moderate Match' : 'Alignment Needed'}
            </h3>
          </div>
          <div className="flex items-center gap-sm flex-wrap justify-end">
            <div className="bg-primary text-white px-4 py-1.5 rounded-full text-xs font-bold shadow-sm">
              ATS SCORE: {evaluationResult.score_100}/100
            </div>
            {scoreTier && TIER_CONFIG[scoreTier] && (
              <span className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-bold border ${TIER_CONFIG[scoreTier].bg} ${TIER_CONFIG[scoreTier].color} ${TIER_CONFIG[scoreTier].border}`}>
                <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>{TIER_CONFIG[scoreTier].icon}</span>
                {TIER_CONFIG[scoreTier].label}
              </span>
            )}
            {interviewState === 'NOT_STARTED' && (
              scoreTier === 'FUNDAMENTALS' ? (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1">
                  <span className="material-symbols-outlined text-sm">block</span>
                  Mock Locked — Study Fundamentals First
                </div>
              ) : (
                <Button
                  variant="gradient"
                  onClick={handleStartInterview}
                  disabled={isStartingInterview}
                  icon="forum"
                  className="px-5 py-1.5 text-xs font-bold rounded-full shadow-sm"
                >
                  {isStartingInterview ? <LoadingSpinner size="sm" /> : 'Start Mock Interview'}
                </Button>
              )
            )}
          </div>
        </div>

        {/* Middle Row */}
        <div className="p-lg grid grid-cols-1 md:grid-cols-3 gap-lg">
          {/* Overall Fit */}
          <div className="flex flex-col items-center text-center">
            <div className="relative w-32 h-32 mb-sm">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 128 128">
                <circle className="text-surface-container-high" cx="64" cy="64" fill="transparent" r="56" stroke="currentColor" strokeWidth="8"></circle>
                <circle className="text-primary" cx="64" cy="64" fill="transparent" r="56" stroke="currentColor" strokeDasharray="351.8" strokeDashoffset={351.8 - (351.8 * evaluationResult.score_100) / 100} strokeLinecap="round" strokeWidth="8"></circle>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center font-bold text-xl text-primary font-h2">{evaluationResult.score_100}%</div>
            </div>
            <h4 className="text-base font-bold text-on-surface mb-xs font-h3">Overall Fit</h4>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              Your profile aligns closely with the core technical requirements.
            </p>
          </div>

          {/* Key Strengths */}
          <div className="space-y-sm">
            <h4 className="text-sm font-bold text-on-surface flex items-center gap-xs font-h3 border-b border-outline-variant/30 pb-xs">
              <span className="material-symbols-outlined text-green-600 text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span> 
              Key Strengths
            </h4>
            <div className="flex flex-wrap gap-xs">
              {evaluationResult.strengths && evaluationResult.strengths.slice(0, 5).map((str, index) => (
                <span key={index} className="bg-green-50 border border-green-200 text-green-900 px-3 py-1 rounded-full text-xs font-semibold">
                  {str}
                </span>
              ))}
              {evaluationResult.strengths && evaluationResult.strengths.length > 5 && (
                <button 
                  onClick={() => setShowAllStrengths(true)} 
                  className="text-xs text-primary font-semibold hover:underline"
                >
                  +{evaluationResult.strengths.length - 5} more
                </button>
              )}
            </div>
          </div>

          {/* Potential Gaps */}
          <div className="space-y-sm">
            <h4 className="text-sm font-bold text-on-surface flex items-center gap-xs font-h3 border-b border-outline-variant/30 pb-xs">
              <span className="material-symbols-outlined text-amber-600 text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span> 
              Potential Gaps
            </h4>
            <div className="flex flex-wrap gap-xs">
              {evaluationResult.gaps && evaluationResult.gaps.slice(0, 5).map((gap, index) => (
                <span key={index} className="bg-orange-50 border border-orange-200 text-primary-container px-3 py-1 rounded-full text-xs font-semibold">
                  {gap}
                </span>
              ))}
              {evaluationResult.gaps && evaluationResult.gaps.length > 5 && (
                <button 
                  onClick={() => setShowAllGaps(true)} 
                  className="text-xs text-primary font-semibold hover:underline"
                >
                  +{evaluationResult.gaps.length - 5} more
                </button>
              )}
            </div>
          </div>
        </div>
      </Card>
    </section>
  );
};
