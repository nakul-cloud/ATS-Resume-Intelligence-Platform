import React, { useState } from 'react';
import { recruiterApi } from '../../api/recruiterApi';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { InputField } from '../../components/common/InputField';
import { SkillPill } from '../../components/common/SkillPill';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';

export const CandidateSearchPage = () => {
  const [jdText, setJdText] = useState('');
  const [candidates, setCandidates] = useState([]);
  const [normalizedJD, setNormalizedJD] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleOpenDetails = (candidate) => {
    // Normalizing matched candidate evaluation results to align with parsedProfile details structure
    const normalized = {
      candidate_name: candidate.candidate_name,
      name: candidate.candidate_name,
      primary_role_title: candidate.primary_role,
      role: candidate.primary_role,
      total_experience_years: candidate.total_experience,
      experience: candidate.total_experience,
      highest_education: candidate.highest_education,
      email: candidate.email,
      phone_number: candidate.phone_number,
      summary_text: candidate.summary_text,
      skills: candidate.skills,
      work_experience: candidate.work_experience,
      projects: candidate.projects,
      accomplishments: candidate.accomplishments,
      hobbies: candidate.hobbies
    };
    setSelectedCandidate(normalized);
    setShowDetailModal(true);
  };

  const handleSearch = async () => {
    if (!jdText || !jdText.trim()) {
      triggerToast('Please provide a Job Description to match against.', 'warning');
      return;
    }

    setIsLoading(true);
    setNormalizedJD(null);
    try {
      // 1. Internally normalize target JD first
      const normResponse = await recruiterApi.normalizeJD(jdText.trim());
      setNormalizedJD(normResponse);
      
      // 2. Query matching profiles
      const response = await recruiterApi.evaluateJD({ jd_text: jdText.trim() });
      const matches = response.results || [];
      matches.sort((a, b) => b.score_100 - a.score_100);
      setCandidates(matches);
      triggerToast(`Search complete! Found ${matches.length} matching candidates.`, 'success');
    } catch (err) {
      console.error(err);
      triggerToast('Failed to evaluate candidates against JD.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-lg">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-lg">
        {/* Left Column: Sourcing JD Target */}
        <div className="lg:col-span-5 space-y-md">
          <Card variant="raised" className="space-y-md">
            <h3 className="font-h3 text-primary font-semibold flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-2xl">groups</span>
              Match Candidates
            </h3>
            
            <InputField 
              label="TARGET JOB DESCRIPTION"
              placeholder="Paste job description to search candidate pool..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              isTextArea={true}
              rows={12}
              disabled={isLoading}
            />

            <Button 
              variant="gradient" 
              onClick={handleSearch}
              disabled={isLoading}
              className="w-full shimmer-sweep"
              icon="search"
            >
              {isLoading ? <LoadingSpinner size="sm" /> : 'Find Matching Candidates'}
            </Button>
          </Card>
        </div>

        {/* Right Column: Ranked Matches Results */}
        <div className="lg:col-span-7 space-y-md">
          {isLoading ? (
            <Card variant="raised" className="h-full flex items-center justify-center p-xl">
              <LoadingSpinner size="lg" />
            </Card>
          ) : candidates.length > 0 ? (
            <div className="space-y-sm animate-fade-in">
              {/* Normalized JD Attributes details */}
              {normalizedJD && (
                <Card variant="raised" className="space-y-sm border border-outline-variant/30 bg-surface-container-lowest/30 animate-fade-in mb-md">
                  <h4 className="font-bold text-primary text-sm flex items-center gap-xs border-b border-outline-variant/30 pb-xs">
                    <span className="material-symbols-outlined text-sm font-bold">auto_fix_high</span>
                    Normalized Job Target Details
                  </h4>
                  <div className="grid grid-cols-2 gap-sm text-xs">
                    <div className="bg-surface-container-low/50 p-xs rounded-xl border border-outline-variant/20">
                      <span className="text-[10px] uppercase text-outline block font-semibold font-label-caps">Extracted Role</span>
                      <span className="text-on-surface font-semibold capitalize">{normalizedJD.role || 'N/A'}</span>
                    </div>
                    <div className="bg-surface-container-low/50 p-xs rounded-xl border border-outline-variant/20">
                      <span className="text-[10px] uppercase text-outline block font-semibold font-label-caps">Extracted Domain</span>
                      <span className="text-on-surface font-semibold capitalize">{normalizedJD.domain || 'N/A'}</span>
                    </div>
                  </div>
                  {normalizedJD.skills && normalizedJD.skills.length > 0 && (
                    <div className="space-y-xs pt-xs">
                      <span className="text-[10px] uppercase text-outline block font-semibold font-label-caps">Target Skills Required</span>
                      <div className="flex flex-wrap gap-xs">
                        {normalizedJD.skills.map((skill, index) => (
                          <SkillPill key={index} skill={skill} className="text-[10px] py-0 px-2 bg-[#E0F2E9] text-green-950 border border-[#A5D6A7]" />
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              )}

              <h3 className="text-lg font-bold text-primary font-h3 mb-xs">
                Ranked Candidates Pool ({candidates.length})
              </h3>
              {candidates.map((candidate, idx) => (
                <Card 
                  key={idx} 
                  variant="raised" 
                  className="flex items-center justify-between p-md border border-outline-variant/30 hover:translate-y-[-2px] transition-all duration-200"
                >
                  <div className="space-y-xs flex-1 mr-4">
                    <div className="flex items-center gap-sm">
                      <span className="font-bold text-on-surface text-base font-h3">
                        {candidate.candidate_name}
                      </span>
                      <span className="text-[10px] uppercase tracking-wider text-outline bg-surface-container-high px-2 py-0.5 rounded font-bold font-mono">
                        ID: {candidate.candidate_id}
                      </span>
                    </div>
                    
                    <p className="text-xs text-on-surface-variant font-medium">
                      Primary Role: {candidate.primary_role || 'Software Developer'}
                    </p>
                    
                    {candidate.skills && candidate.skills.length > 0 && (
                      <div className="flex flex-wrap gap-xs mt-xs">
                        {candidate.skills.slice(0, 4).map((s, sIdx) => (
                          <SkillPill key={sIdx} skill={s} className="text-[10px] py-0 px-2" />
                        ))}
                        {candidate.skills.length > 4 && (
                          <span className="text-[10px] text-outline font-semibold">
                            +{candidate.skills.length - 4} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="text-right flex flex-col items-end gap-xs flex-shrink-0">
                    <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps font-semibold">
                      Match Rating
                    </span>
                    <span className={`text-2xl font-bold font-mono ${
                      candidate.score_100 >= 80 ? 'text-green-600' : 'text-primary'
                    }`}>
                      {candidate.score_100}%
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      candidate.score_100 >= 80 ? 'bg-[#E0F2E9] text-green-800' : 'bg-orange-50 text-primary-container'
                    }`}>
                      {candidate.score_100 >= 80 ? 'High Fit' : 'Medium Fit'}
                    </span>
                    <Button 
                      variant="ghost" 
                      onClick={() => handleOpenDetails(candidate)}
                      className="text-xs px-2.5 py-1 mt-sm"
                      icon="visibility"
                    >
                      See Details
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card variant="raised" className="h-full flex flex-col items-center justify-center text-center p-xl opacity-60">
              <span className="material-symbols-outlined text-6xl text-outline mb-md">person_search</span>
              <h3 className="font-h3 text-on-surface font-semibold mb-xs">No Candidates Loaded</h3>
              <p className="text-sm text-outline max-w-[320px]">
                Paste a target job description on the left panel to query pgvector and find matching candidates dynamically.
              </p>
            </Card>
          )}
        </div>
      </div>

      {/* Neomorphic Details Modal with Blurred Background */}
      {showDetailModal && selectedCandidate && (
        <div className="fixed inset-0 bg-surface/80 backdrop-blur-md z-50 flex items-center justify-center p-md animate-fade-in">
          <div className="bg-surface max-w-[800px] w-full max-h-[85vh] overflow-y-auto rounded-3xl p-lg border border-outline-variant shadow-2xl space-y-md relative neomorphic-raised">
            <button 
              onClick={() => {
                setShowDetailModal(false);
                setSelectedCandidate(null);
              }}
              className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center bg-surface border border-outline-variant text-on-surface-variant hover:text-primary neomorphic-raised active:neomorphic-inset transition-all"
            >
              <span className="material-symbols-outlined">close</span>
            </button>

            <h3 className="font-h3 text-primary font-semibold border-b border-outline-variant pb-xs flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-2xl">account_circle</span>
              Candidate Sourcing Profile Details
            </h3>

            {/* Header info grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-md text-xs bg-surface-container-low p-md rounded-2xl border border-outline-variant/30">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Full Name</span>
                <span className="text-on-surface font-semibold text-sm capitalize">{selectedCandidate.candidate_name || selectedCandidate.name || 'N/A'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Education Level</span>
                <span className="text-on-surface font-semibold text-sm capitalize">{selectedCandidate.highest_education || 'N/A'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Target Role & Domain</span>
                <span className="text-on-surface font-semibold text-sm capitalize">
                  {selectedCandidate.primary_role_title || selectedCandidate.role || 'N/A'} ({selectedCandidate.primary_domain || 'N/A'})
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Contact Email & Phone</span>
                <span className="text-on-surface font-semibold text-sm">
                  {selectedCandidate.email || 'N/A'} • {selectedCandidate.phone_number || 'N/A'}
                </span>
              </div>
            </div>

            {/* Professional Summary */}
            <div className="space-y-xs">
              <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Professional Summary</span>
              <p className="text-xs text-on-surface-variant leading-relaxed bg-surface-container-low p-md rounded-2xl border border-outline-variant/30">
                {selectedCandidate.summary_text || 'No summary parsed.'}
              </p>
            </div>

            {/* Technical Skills */}
            <div className="space-y-xs">
              <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Skills Overview</span>
              <div className="flex flex-wrap gap-xs bg-surface-container-low p-md rounded-2xl border border-outline-variant/30">
                {selectedCandidate.skills && selectedCandidate.skills.map((skill, index) => (
                  <SkillPill key={index} skill={typeof skill === 'string' ? skill : (skill.skill_name || '')} />
                ))}
              </div>
            </div>

            {/* Employment History */}
            {selectedCandidate.work_experience && selectedCandidate.work_experience.length > 0 && (
              <div className="space-y-sm">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Work History</span>
                <div className="space-y-sm">
                  {selectedCandidate.work_experience.map((work, idx) => (
                    <div key={idx} className="bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30">
                      <div className="flex justify-between items-start">
                        <div>
                          <h6 className="font-semibold text-on-surface text-xs">{work.role || 'Job Title'}</h6>
                          <p className="text-[10px] text-secondary font-medium">{work.company || 'Company'}</p>
                        </div>
                        <span className="text-[10px] bg-surface-container-high text-on-surface-variant px-2 py-0.5 rounded border border-outline-variant">
                          {work.duration || 'N/A'}
                        </span>
                      </div>
                      {work.bullets && work.bullets.length > 0 && (
                        <ul className="list-disc pl-5 mt-xs space-y-xs">
                          {work.bullets.map((bullet, bIdx) => (
                            <li key={bIdx} className="text-[11px] text-on-surface-variant leading-relaxed">
                              {bullet}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Key Projects */}
            {selectedCandidate.projects && selectedCandidate.projects.length > 0 && (
              <div className="space-y-sm">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Key Projects</span>
                <div className="space-y-sm">
                  {selectedCandidate.projects.map((proj, idx) => (
                    <div key={idx} className="bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30">
                      <h6 className="font-semibold text-on-surface text-xs">{proj.title || 'Project Name'}</h6>
                      <p className="text-[11px] text-on-surface-variant mt-xs leading-relaxed">{proj.description}</p>
                      {proj.technologies_used && proj.technologies_used.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-sm">
                          {proj.technologies_used.map((tech, tIdx) => (
                            <span key={tIdx} className="text-[9px] font-bold bg-[#E0F2E9] text-green-950 border border-[#A5D6A7] px-2 py-0.5 rounded-full">
                              {tech}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Hobbies and Accomplishments Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-md pt-xs">
              {/* Accomplishments */}
              <div className="space-y-xs">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Accomplishments</span>
                {selectedCandidate.accomplishments && selectedCandidate.accomplishments.length > 0 ? (
                  <ul className="list-disc pl-5 text-xs text-on-surface-variant space-y-xs bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30 min-h-[100px]">
                    {selectedCandidate.accomplishments.map((acc, idx) => (
                      <li key={idx} className="leading-relaxed">{acc}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-outline italic bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30 text-center min-h-[100px] flex items-center justify-center">No accomplishments parsed.</p>
                )}
              </div>

              {/* Hobbies */}
              <div className="space-y-xs">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Hobbies & Interests</span>
                {selectedCandidate.hobbies && selectedCandidate.hobbies.length > 0 ? (
                  <div className="flex flex-wrap gap-xs bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30 min-h-[100px] items-start content-start">
                    {selectedCandidate.hobbies.map((hobby, idx) => (
                      <span key={idx} className="bg-surface-container-high text-on-surface-variant text-[10px] px-2.5 py-0.5 rounded-full border border-outline-variant">
                        {hobby}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-outline italic bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30 text-center min-h-[100px] flex items-center justify-center">No hobbies parsed.</p>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-sm">
              <Button onClick={() => {
                setShowDetailModal(false);
                setSelectedCandidate(null);
              }}>Close Details</Button>
            </div>
          </div>
        </div>
      )}

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
