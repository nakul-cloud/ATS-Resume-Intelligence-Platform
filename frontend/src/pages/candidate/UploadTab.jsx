import React, { useState, useRef } from 'react';
import { useCandidateStore } from '../../store/candidateStore';
import { useAuthStore } from '../../store/authStore';
import { candidateApi } from '../../api/candidateApi';
import { Button } from '../../components/common/Button';
import { Card } from '../../components/common/Card';
import { SkillPill } from '../../components/common/SkillPill';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';

export const UploadTab = ({ onTabChange }) => {
  const { setParsedProfile, parsedProfile, candidateId } = useCandidateStore();
  const recruiterRole = useAuthStore((state) => state.role === 'recruiter');
  
  const [file, setFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPersisting, setIsPersisting] = useState(false);
  
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');
  const fileInputRef = useRef(null);

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile);
    } else {
      triggerToast('Only PDF files are supported.', 'warning');
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      triggerToast('Only PDF files are supported.', 'warning');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      triggerToast('Please select a resume PDF first.', 'warning');
      return;
    }

    setIsLoading(true);
    try {
      const response = await candidateApi.uploadResume(file);
      if (response.status === 'success') {
        setParsedProfile(response.parsed_data, response.candidate_id);
        triggerToast('Resume uploaded and parsed successfully!', 'success');
      } else {
        triggerToast(response.message || 'Parsing failed.', 'error');
      }
    } catch (err) {
      console.error(err);
      triggerToast('Failed to parse resume. Is backend running?', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePersist = async () => {
    if (!parsedProfile) return;

    setIsPersisting(true);
    try {
      const response = await candidateApi.persist(parsedProfile);
      if (response.status === 'success') {
        // Update stored profile with new persisted candidate ID
        setParsedProfile(parsedProfile, response.candidate_id);
        triggerToast(`Candidate explicitly saved to DB! ID: ${response.candidate_id}`, 'success');
      } else {
        triggerToast(response.message || 'Persistence failed.', 'error');
      }
    } catch (err) {
      console.error(err);
      triggerToast('Failed to persist candidate profile.', 'error');
    } finally {
      setIsPersisting(false);
    }
  };

  return (
    <div className="max-w-[800px] mx-auto space-y-lg">
      <Card variant="raised" className="text-center relative overflow-hidden p-xl">
        <div className="absolute top-0 right-0 p-4 opacity-10">
          <span className="material-symbols-outlined text-9xl text-outline">description</span>
        </div>
        
        <div className="w-20 h-20 bg-primary-container/10 rounded-full flex items-center justify-center mx-auto mb-md animate-pulse">
          <span className="material-symbols-outlined text-primary-container text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>
            upload_file
          </span>
        </div>
        
        <h2 className="font-h2 text-h2 text-primary mb-sm">Upload Resume</h2>
        <p className="font-body-md text-on-surface-variant mb-lg">
          Our parser will extract details from your resume PDF.
        </p>

        {/* Drag & Drop Zone */}
        <div 
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-outline-variant bg-surface-container-low/50 hover:bg-surface-container/60 rounded-2xl p-xl mb-lg group hover:border-primary-container transition-all cursor-pointer neomorphic-inset flex flex-col items-center justify-center"
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileSelect} 
            className="hidden" 
            accept="application/pdf"
          />
          <span className="material-symbols-outlined text-5xl text-secondary mb-base group-hover:text-primary-container transition-colors">
            cloud_upload
          </span>
          <p className="font-body-md text-on-secondary-container font-semibold">
            {file ? file.name : 'Drag & drop your resume PDF here or click to browse'}
          </p>
          <p className="text-xs text-outline mt-xs">Maximum file size: 5MB (PDF only)</p>
        </div>

        <Button 
          variant="gradient" 
          onClick={handleUpload}
          disabled={isLoading || !file}
          className="mx-auto px-10 py-4 shimmer-sweep"
          icon="auto_fix_high"
        >
          {isLoading ? <LoadingSpinner size="sm" /> : 'Upload & Parse'}
        </Button>
      </Card>

      {/* Parse Result panel */}
      {parsedProfile && (
        <div className="bg-[#E0F2E9]/60 border border-[#A5D6A7] rounded-3xl p-md flex items-start gap-md animate-fade-in">
          <div className="bg-green-100 p-2 rounded-full text-green-700">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
              check_circle
            </span>
          </div>
          
          <div className="flex-1">
            <h4 className="font-bold text-green-900 mb-xs">Resume uploaded successfully!</h4>
            <p className="text-xs text-green-800/80 leading-relaxed">
              Your resume details have been processed. You can now proceed to run AI evaluations against target job roles.
            </p>
            
            <div className="flex justify-end mt-sm">
              <Button variant="ghost" onClick={() => onTabChange('evaluate')} className="bg-white/80 hover:bg-white border-green-300 text-green-800 text-xs px-3 py-1.5" icon="east">
                Proceed to Self Evaluation
              </Button>
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
