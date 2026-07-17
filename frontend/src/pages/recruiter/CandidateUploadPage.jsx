import React, { useState } from 'react';
import { recruiterApi } from '../../api/recruiterApi';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';
import { SkillPill } from '../../components/common/SkillPill';

export const CandidateUploadPage = () => {
  const [file, setFile] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [parsedProfile, setParsedProfile] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === 'application/pdf') {
      setFile(droppedFile);
    } else {
      triggerToast('Only PDF files are supported.', 'warning');
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile?.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      triggerToast('Only PDF files are supported.', 'warning');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      triggerToast('Please select a resume PDF file to upload.', 'warning');
      return;
    }

    setIsLoading(true);
    setParsedProfile(null);
    try {
      const response = await recruiterApi.uploadResume(file);
      if (response.success && response.data) {
        const resumeId = response.data.resume_id;

        if (response.data.status === "PENDING" && resumeId) {
          let attempts = 0;
          const maxAttempts = 30; // Poll for max 30 seconds

          const pollInterval = setInterval(async () => {
            attempts += 1;
            try {
              const statusResponse = await recruiterApi.getResumeStatus(resumeId);
              if (statusResponse.status === "success" && statusResponse.data) {
                const parseStatus = statusResponse.data.status;
                const candidateId = statusResponse.data.candidate_id;

                if (parseStatus === "SUCCESS" && candidateId) {
                  clearInterval(pollInterval);
                  const candidateResponse = await recruiterApi.getCandidate(candidateId);
                  if (candidateResponse.status === "success" && candidateResponse.parsed_data) {
                    setParsedProfile(candidateResponse.parsed_data);
                    triggerToast('Resume parsed and indexed successfully!', 'success');
                  } else {
                    triggerToast('Failed to fetch parsed candidate details.', 'error');
                  }
                  setIsLoading(false);
                } else if (parseStatus === "FAILED") {
                  clearInterval(pollInterval);
                  triggerToast(statusResponse.data.error_message || 'Resume parsing failed on worker.', 'error');
                  setIsLoading(false);
                }
              }
            } catch (pollErr) {
              console.error("Polling error:", pollErr);
            }

            if (attempts >= maxAttempts) {
              clearInterval(pollInterval);
              triggerToast('Parsing timeout. Please check dashboard status later.', 'warning');
              setIsLoading(false);
            }
          }, 1000);

        } else if (response.data.parsed_data) {
          setParsedProfile(response.data.parsed_data);
          triggerToast('Resume parsed and indexed successfully!', 'success');
          setIsLoading(false);
        } else {
          triggerToast('Uploaded, but status is unknown.', 'warning');
          setIsLoading(false);
        }
      } else {
        triggerToast(response.message || 'Failed to upload resume.', 'error');
        setIsLoading(false);
      }
    } catch (err) {
      console.error(err);
      triggerToast('Failed to process resume parsing.', 'error');
      setIsLoading(false);
    }
  };

  const renderRightColumn = () => {
    if (isLoading) {
      return (
        <Card variant="raised" className="h-full flex items-center justify-center p-xl min-h-[300px]">
          <LoadingSpinner size="lg" />
        </Card>
      );
    }

    if (parsedProfile) {
      return (
        <div className="space-y-md animate-fade-in">
          <h3 className="text-lg font-bold text-primary font-h3">
            Successfully Parsed Candidate Details
          </h3>
          
          <Card variant="raised" className="space-y-md border border-outline-variant/30">
            <div className="flex justify-between items-start border-b border-outline-variant/50 pb-sm">
              <div>
                <h4 className="font-bold text-on-surface text-lg">{parsedProfile.candidate_name || parsedProfile.name}</h4>
                <p className="text-xs text-on-surface-variant mt-xs">
                  {parsedProfile.primary_role_title || parsedProfile.role || 'Software Developer'} • {parsedProfile.total_experience_years || parsedProfile.experience || 0.0} Years Experience
                </p>
              </div>
              <div className="flex flex-col items-end gap-xs">
                <span className="text-[10px] uppercase tracking-wider text-outline bg-surface-container-high px-2.5 py-1 rounded font-bold font-mono">
                  SUCCESS
                </span>
                <Button 
                  variant="ghost" 
                  onClick={() => setShowDetailModal(true)} 
                  className="text-xs px-2.5 py-1 mt-xs"
                  icon="visibility"
                >
                  See More Details
                </Button>
              </div>
            </div>

            {/* Contact Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-sm text-xs text-on-surface-variant font-medium">
              <div className="flex items-center gap-xs">
                <span className="material-symbols-outlined text-sm">mail</span>
                {parsedProfile.email || 'N/A'}
              </div>
              <div className="flex items-center gap-xs">
                <span className="material-symbols-outlined text-sm">call</span>
                {parsedProfile.phone_number || 'N/A'}
              </div>
            </div>

            {/* Summary */}
            <div className="space-y-xs pt-xs">
              <h5 className="font-bold text-on-surface text-sm">Professional Summary</h5>
              <p className="text-xs text-on-surface-variant leading-relaxed line-clamp-3">
                {parsedProfile.summary_text || 'No summary details parsed.'}
              </p>
            </div>

            {/* Technical Skills */}
            <div className="space-y-xs pt-xs">
              <h5 className="font-bold text-on-surface text-sm">Technical Skills</h5>
              <div className="flex flex-wrap gap-xs">
                {parsedProfile.skills?.slice(0, 8).map((skill, index) => {
                  const skillName = typeof skill === 'string' ? skill : (skill.skill_name || '');
                  const skillKey = skillName || index;
                  return <SkillPill key={skillKey} skill={skillName} />;
                })}
                {parsedProfile.skills && parsedProfile.skills.length > 8 && (
                  <span className="text-xs text-outline font-semibold self-center ml-xs">
                    +{parsedProfile.skills.length - 8} more
                  </span>
                )}
              </div>
            </div>
          </Card>
        </div>
      );
    }

    return (
      <Card variant="raised" className="h-full flex flex-col items-center justify-center text-center p-xl opacity-60 min-h-[300px]">
        <span className="material-symbols-outlined text-6xl text-outline mb-md">upload_file</span>
        <h3 className="font-h3 text-on-surface font-semibold mb-xs">No Candidate Loaded</h3>
        <p className="text-sm text-outline max-w-[320px]">
          Upload and parse candidate resume files to index them in the database for recruiter matchmaking.
        </p>
      </Card>
    );
  };

  return (
    <div className="space-y-lg">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-lg">
        {/* Left Column: Drag & Drop Resume File Uploader */}
        <div className="lg:col-span-5 space-y-md">
          <Card variant="raised" className="space-y-md">
            <h3 className="font-h3 text-primary font-semibold flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-2xl">upload_file</span>
              {' '}Upload Resume
            </h3>
            
            <div 
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-3xl p-lg text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[220px] ${
                isDragOver 
                  ? 'border-primary bg-primary/5 scale-[0.99]' 
                  : 'border-outline-variant hover:border-primary/50'
              }`}
            >
              <input 
                type="file" 
                id="recruiter-file-upload" 
                className="hidden" 
                accept=".pdf"
                onChange={handleFileSelect}
              />
              <label htmlFor="recruiter-file-upload" className="cursor-pointer w-full h-full flex flex-col items-center justify-center space-y-sm">
                <span className="material-symbols-outlined text-4xl text-outline-variant animate-pulse">cloud_upload</span>
                {file ? (
                  <div className="space-y-xs">
                    <p className="font-bold text-on-surface truncate max-w-[280px]">{file.name}</p>
                    <p className="text-xs text-outline">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-semibold text-on-surface">Drag & Drop Resume here</p>
                    <p className="text-xs text-outline mt-xs">or click to browse local files (PDF only)</p>
                  </div>
                )}
              </label>
            </div>

            <Button 
              variant="gradient" 
              onClick={handleUpload}
              disabled={isLoading || !file}
              className="w-full shimmer-sweep"
              icon="upload"
            >
              {isLoading ? <LoadingSpinner size="sm" /> : 'Parse & Index Resume'}
            </Button>
          </Card>
        </div>

        {/* Right Column: Parsed Results display */}
        <div className="lg:col-span-7 space-y-md">
          {renderRightColumn()}
        </div>
      </div>

      {/* Neomorphic Details Modal with Blurred Background */}
      {showDetailModal && parsedProfile && (
        <div className="fixed inset-0 bg-surface/80 backdrop-blur-md z-50 flex items-center justify-center p-md animate-fade-in">
          <div className="bg-surface max-w-[800px] w-full max-h-[85vh] overflow-y-auto rounded-3xl p-lg border border-outline-variant shadow-2xl space-y-md relative neomorphic-raised">
            <button 
              onClick={() => setShowDetailModal(false)}
              className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center bg-surface border border-outline-variant text-on-surface-variant hover:text-primary neomorphic-raised active:neomorphic-inset transition-all"
            >
              <span className="material-symbols-outlined">close</span>
            </button>

            <h3 className="font-h3 text-primary font-semibold border-b border-outline-variant pb-xs flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-2xl">account_circle</span>
              {' '}Candidate Sourcing Profile Details
            </h3>

            {/* Header info grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-md text-xs bg-surface-container-low p-md rounded-2xl border border-outline-variant/30">
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Full Name</span>
                <span className="text-on-surface font-semibold text-sm capitalize">{parsedProfile.candidate_name || parsedProfile.name || 'N/A'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Education Level</span>
                <span className="text-on-surface font-semibold text-sm capitalize">{parsedProfile.highest_education || 'N/A'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Target Role & Domain</span>
                <span className="text-on-surface font-semibold text-sm capitalize">
                  {parsedProfile.primary_role_title || parsedProfile.role || 'N/A'} ({parsedProfile.primary_domain || 'N/A'})
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Contact Email & Phone</span>
                <span className="text-on-surface font-semibold text-sm">
                  {parsedProfile.email || 'N/A'} • {parsedProfile.phone_number || 'N/A'}
                </span>
              </div>
            </div>

            {/* Professional Summary */}
            <div className="space-y-xs">
              <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Professional Summary</span>
              <p className="text-xs text-on-surface-variant leading-relaxed bg-surface-container-low p-md rounded-2xl border border-outline-variant/30">
                {parsedProfile.summary_text || 'No summary parsed.'}
              </p>
            </div>

            {/* Technical Skills */}
            <div className="space-y-xs">
              <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Skills Overview</span>
              <div className="flex flex-wrap gap-xs bg-surface-container-low p-md rounded-2xl border border-outline-variant/30">
                {parsedProfile.skills?.map((skill, index) => {
                  const skillName = typeof skill === 'string' ? skill : (skill.skill_name || '');
                  const skillKey = skillName || index;
                  return <SkillPill key={skillKey} skill={skillName} />;
                })}
              </div>
            </div>

            {/* Employment History */}
            {parsedProfile.work_experience && parsedProfile.work_experience.length > 0 && (
              <div className="space-y-sm">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Work History</span>
                <div className="space-y-sm">
                  {parsedProfile.work_experience.map((work, idx) => {
                    const workKey = work.company ? `${work.company}-${work.role}-${idx}` : idx;
                    return (
                      <div key={workKey} className="bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30">
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
                            {work.bullets.map((bullet, bIdx) => {
                              const bulletKey = `${bullet.substring(0, 15)}-${bIdx}`;
                              return (
                                <li key={bulletKey} className="text-[11px] text-on-surface-variant leading-relaxed">
                                  {bullet}
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Key Projects */}
            {parsedProfile.projects && parsedProfile.projects.length > 0 && (
              <div className="space-y-sm">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Key Projects</span>
                <div className="space-y-sm">
                  {parsedProfile.projects.map((proj, idx) => {
                    const projKey = proj.title ? `${proj.title}-${idx}` : idx;
                    return (
                      <div key={projKey} className="bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30">
                        <h6 className="font-semibold text-on-surface text-xs">{proj.title || 'Project Name'}</h6>
                        <p className="text-[11px] text-on-surface-variant mt-xs leading-relaxed">{proj.description}</p>
                        {proj.technologies_used && proj.technologies_used.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-sm">
                            {proj.technologies_used.map((tech) => (
                              <span key={tech} className="text-[9px] font-bold bg-[#E0F2E9] text-green-950 border border-[#A5D6A7] px-2 py-0.5 rounded-full">
                                {tech}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Hobbies and Accomplishments Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-md pt-xs">
              {/* Accomplishments */}
              <div className="space-y-xs">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Accomplishments</span>
                {parsedProfile.accomplishments && parsedProfile.accomplishments.length > 0 ? (
                  <ul className="list-disc pl-5 text-xs text-on-surface-variant space-y-xs bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30 min-h-[100px]">
                    {parsedProfile.accomplishments.map((acc, idx) => {
                      const accKey = `${acc.substring(0, 15)}-${idx}`;
                      return <li key={accKey} className="leading-relaxed">{acc}</li>;
                    })}
                  </ul>
                ) : (
                  <p className="text-xs text-outline italic bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30 text-center min-h-[100px] flex items-center justify-center">No accomplishments parsed.</p>
                )}
              </div>

              {/* Hobbies */}
              <div className="space-y-xs">
                <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps">Hobbies & Interests</span>
                {parsedProfile.hobbies && parsedProfile.hobbies.length > 0 ? (
                  <div className="flex flex-wrap gap-xs bg-surface-container-low p-sm rounded-2xl border border-outline-variant/30 min-h-[100px] items-start content-start">
                    {parsedProfile.hobbies.map((hobby) => (
                      <span key={hobby} className="bg-surface-container-high text-on-surface-variant text-[10px] px-2.5 py-0.5 rounded-full border border-outline-variant">
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
              <Button onClick={() => setShowDetailModal(false)}>Close Details</Button>
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
