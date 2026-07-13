import React, { useState, useEffect } from 'react';
import { useCandidateStore } from '../../store/candidateStore';
import { candidateApi } from '../../api/candidateApi';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { ActiveProfileBadge } from '../../components/common/ActiveProfileBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';

export const ProjectsTab = () => {
  const { parsedProfile, candidateId, evaluationResult, projectResults, setProjectResults, clearSession } = useCandidateStore();
  
  const [jobId, setJobId] = useState('');
  const [evalId, setEvalId] = useState('');
  const [scoreInput, setScoreInput] = useState('');
  const [targetDomain, setTargetDomain] = useState('Full Stack Engineering');
  const [skillGapsInput, setSkillGapsInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');

  // Load initial evaluation gaps if available
  useEffect(() => {
    if (evaluationResult) {
      setScoreInput(evaluationResult.score_100 || '');
      if (evaluationResult.gaps && evaluationResult.gaps.length > 0) {
        setSkillGapsInput(evaluationResult.gaps.join(', '));
      }
    }
  }, [evaluationResult]);

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleGetProjects = async () => {
    setIsLoading(true);
    try {
      const gapsArray = skillGapsInput
        ? skillGapsInput.split(',').map(s => s.trim()).filter(Boolean)
        : ["System Architecture", "Async programming"];

      const payload = {
        candidate_id: candidateId || null,
        candidate_data: candidateId ? null : parsedProfile,
        gaps: gapsArray
      };
      
      const response = await candidateApi.getProjects(payload);
      setProjectResults(response);
      triggerToast('Project recommendations retrieved successfully!', 'success');
    } catch (err) {
      console.error(err);
      triggerToast('Failed to retrieve project recommendations.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const getDifficultyStyles = (level) => {
    const lvl = (level || '').toLowerCase();
    if (lvl.includes('high') || lvl.includes('critical') || lvl.includes('hard')) {
      return { borderClass: 'border-l-4 border-l-red-500', pillClass: 'bg-red-50 text-red-700 border-red-200' };
    } else if (lvl.includes('inter') || lvl.includes('signif') || lvl.includes('med')) {
      return { borderClass: 'border-l-4 border-l-amber-500', pillClass: 'bg-amber-50 text-amber-700 border-amber-200' };
    } else if (lvl.includes('refine') || lvl.includes('yellow') || lvl.includes('low')) {
      return { borderClass: 'border-l-4 border-l-yellow-400', pillClass: 'bg-yellow-50 text-yellow-700 border-yellow-200' };
    } else {
      return { borderClass: 'border-l-4 border-l-green-500', pillClass: 'bg-green-50 text-green-700 border-green-200' };
    }
  };

  return (
    <div className="space-y-lg max-w-[1100px] mx-auto pb-16">
      {/* Hero Section */}
      <div className="mb-lg space-y-xs">
        <h2 className="font-h1 text-h1 text-primary font-bold">Strategic Project Lab</h2>
        <p className="font-body-md text-on-surface-variant">
          Close your technical gaps and boost your ATS score by completing curated projects designed to highlight the specific skills recruiters in your domain are searching for.
        </p>
      </div>

      {/* Input parameters card */}
      <Card variant="raised" className="p-lg">
        <div className="space-y-md">
          <div className="flex items-center gap-2 mb-xs border-b border-outline-variant/30 pb-sm">
            <span className="material-symbols-outlined text-primary text-xl">analytics</span>
            <h3 className="text-base font-bold font-h2 text-on-surface">Analysis Parameters</h3>
          </div>
          
          <ActiveProfileBadge onClear={clearSession} />

          <div className="space-y-xs pt-xs">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block font-label-caps">Identified Skill Gaps</label>
            <textarea 
              className="w-full bg-white border border-outline-variant rounded-xl p-4 text-xs text-on-surface focus:ring-1 focus:ring-primary outline-none resize-none transition-all" 
              placeholder="List skills separated by commas (e.g. Redis, Docker, System Design, GraphQL...)" 
              rows="3"
              value={skillGapsInput}
              onChange={(e) => setSkillGapsInput(e.target.value)}
            />
          </div>

          <div className="flex justify-end pt-sm border-t border-outline-variant/30">
            <Button 
              variant="gradient" 
              onClick={handleGetProjects}
              disabled={isLoading}
              className="px-8 py-3 text-xs font-bold"
              icon="auto_awesome"
            >
              {isLoading ? <LoadingSpinner size="sm" /> : 'Get Project Recommendations'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Project Results List */}
      {projectResults && projectResults.length > 0 ? (
        <section className="space-y-lg animate-fade-in pt-lg">
          <h3 className="text-2xl font-bold font-h2 text-primary border-b border-outline-variant/30 pb-sm">Personalized Roadmap</h3>
          
          <div className="space-y-md">
            {projectResults.map((project, index) => {
              const diffStyles = getDifficultyStyles(project.difficulty_level);
              return (
                <Card 
                  key={index} 
                  variant="raised" 
                  className={`p-lg flex flex-col md:flex-row gap-lg transition-all duration-300 group hover:shadow-xl ${diffStyles.borderClass}`}
                >
                  <div className="flex-none">
                    <div className="w-16 h-16 rounded-full bg-primary/10 border border-primary/20 text-primary flex items-center justify-center font-bold text-2xl font-h2">
                      {index + 1}
                    </div>
                  </div>

                  <div className="flex-grow flex flex-col gap-md">
                    <div className="flex flex-wrap items-center justify-between gap-sm">
                      <h4 className="text-lg font-bold font-h2 text-on-surface group-hover:text-primary transition-colors">
                        {project.project_title}
                      </h4>
                      <div className="flex flex-wrap gap-xs">
                        <span className={`border px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${diffStyles.pillClass}`}>
                          {project.difficulty_level || 'High Impact'}
                        </span>
                        <span className="bg-primary/10 border border-primary/20 text-primary px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider">
                          Architectural
                        </span>
                        <span className="bg-surface-container-high border border-outline-variant text-on-surface-variant px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider">
                          {project.time_estimate || '~20 Hours'}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      {project.project_description}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-md pt-xs">
                      <div className="bg-surface-container-low/40 border border-outline-variant/30 rounded-xl p-md">
                        <h5 className="text-[10px] font-bold text-on-surface-variant uppercase mb-2 tracking-widest font-label-caps">Key Outcome</h5>
                        <p className="text-xs text-on-surface-variant leading-relaxed">
                          {project.expected_outcome}
                        </p>
                      </div>
                      <div className="bg-surface-container-low/40 border border-outline-variant/30 rounded-xl p-md">
                        <h5 className="text-[10px] font-bold text-on-surface-variant uppercase mb-2 tracking-widest font-label-caps">Tools &amp; Datasets</h5>
                        <div className="flex flex-wrap gap-xs">
                          {(project.tools_required || []).map((t, idx) => (
                            <span 
                              key={idx} 
                              className="bg-white border border-outline-variant text-on-surface-variant px-2.5 py-0.5 rounded text-[11px] font-medium shadow-sm"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </section>
      ) : (
        <Card variant="raised" className="h-full flex flex-col items-center justify-center text-center p-xl opacity-60 min-h-[300px]">
          <span className="material-symbols-outlined text-6xl text-outline mb-md">rocket_launch</span>
          <h3 className="font-h3 text-on-surface font-semibold mb-xs">No Projects Requested</h3>
          <p className="text-sm text-outline max-w-[320px]">
            Click "Get Project Recommendations" to receive targeted neomorphic development templates built by AI.
          </p>
        </Card>
      )}

      {/* Footer Explainer */}
      <footer className="mt-xl border-t border-outline-variant/40 pt-lg">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-lg items-center">
          <div>
            <h5 className="text-xl font-bold font-h2 text-primary mb-md">Difficulty Mapping &amp; Impact</h5>
            <ul className="flex flex-col gap-sm">
              <li className="flex items-center gap-sm">
                <div className="w-3.5 h-3.5 rounded-full bg-red-500 shrink-0"></div>
                <span className="text-xs text-on-surface-variant"><b className="text-on-surface">Critical Impact:</b> High difficulty, addresses multiple core senior-level skill gaps.</span>
              </li>
              <li className="flex items-center gap-sm">
                <div className="w-3.5 h-3.5 rounded-full bg-amber-500 shrink-0"></div>
                <span className="text-xs text-on-surface-variant"><b className="text-on-surface">Significant Gap:</b> Moderate difficulty, targets missing domain-specific technical tags.</span>
              </li>
              <li className="flex items-center gap-sm">
                <div className="w-3.5 h-3.5 rounded-full bg-yellow-400 shrink-0"></div>
                <span className="text-xs text-on-surface-variant"><b className="text-on-surface">Skill Refinement:</b> Lower difficulty, perfects existing skills for higher ATS confidence.</span>
              </li>
              <li className="flex items-center gap-sm">
                <div className="w-3.5 h-3.5 rounded-full bg-green-500 shrink-0"></div>
                <span className="text-xs text-on-surface-variant"><b className="text-on-surface">Bonus Credential:</b> Fast projects that add "nice-to-have" keywords to your profile.</span>
              </li>
            </ul>
          </div>
          <div className="bg-primary-container/10 rounded-2xl p-lg border border-primary-container/20 text-primary">
            <span className="material-symbols-outlined text-primary text-4xl mb-base">lightbulb</span>
            <p className="text-sm font-semibold leading-relaxed italic font-h2">
              "Recruiters look for evidence, not just mentions. Completing these projects gives you verifiable 'proof of work' that can be linked directly from your resume."
            </p>
          </div>
        </div>
      </footer>

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
