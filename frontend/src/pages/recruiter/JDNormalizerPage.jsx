import React, { useState } from 'react';
import { recruiterApi } from '../../api/recruiterApi';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { InputField } from '../../components/common/InputField';
import { SkillPill } from '../../components/common/SkillPill';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';

export const JDNormalizerPage = () => {
  const [rawJD, setRawJD] = useState('');
  const [normalizedJD, setNormalizedJD] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleNormalize = async () => {
    if (!rawJD || !rawJD.trim()) {
      triggerToast('Please paste a raw Job Description first.', 'warning');
      return;
    }

    setIsLoading(true);
    try {
      const response = await recruiterApi.normalizeJD(rawJD.trim());
      setNormalizedJD(response);
      triggerToast('Job Description normalized successfully!', 'success');
    } catch (err) {
      console.error(err);
      triggerToast('Failed to normalize Job Description.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-lg">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-lg">
        {/* Input Column */}
        <div className="lg:col-span-5 space-y-md">
          <Card variant="raised" className="space-y-md">
            <h3 className="font-h3 text-primary font-semibold flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-2xl">auto_fix_high</span>
              Normalize Job Description
            </h3>
            
            <InputField 
              label="INPUT JOB DESCRIPTION"
              placeholder="Paste raw, messy Job Description text here..."
              value={rawJD}
              onChange={(e) => setRawJD(e.target.value)}
              isTextArea={true}
              rows={12}
              disabled={isLoading}
            />

            <Button 
              variant="gradient" 
              onClick={handleNormalize}
              disabled={isLoading}
              className="w-full shimmer-sweep"
              icon="tune"
            >
              {isLoading ? <LoadingSpinner size="sm" /> : 'Normalize JD (Postgres Caching)'}
            </Button>
          </Card>
        </div>

        {/* Output Column */}
        <div className="lg:col-span-7 space-y-md">
          {normalizedJD ? (
            <Card variant="raised" className="space-y-md animate-fade-in">
              <h3 className="font-h3 text-primary font-semibold border-b border-outline-variant pb-xs">
                Normalized Extraction Results
              </h3>
              
              <div className="grid grid-cols-2 gap-md">
                <div className="bg-surface-container-low p-sm rounded-xl border border-outline-variant">
                  <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps font-semibold">Normalized Title</span>
                  <span className="text-on-surface font-semibold text-sm capitalize">{normalizedJD.role || 'N/A'}</span>
                </div>
                <div className="bg-surface-container-low p-sm rounded-xl border border-outline-variant">
                  <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps font-semibold">Extracted Domain</span>
                  <span className="text-on-surface font-semibold text-sm capitalize">{normalizedJD.domain || 'N/A'}</span>
                </div>
              </div>

              {normalizedJD.skills && normalizedJD.skills.length > 0 && (
                <div className="space-y-xs">
                  <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps font-semibold">Normalized Skills Required</span>
                  <div className="flex flex-wrap gap-xs">
                    {normalizedJD.skills.map((skill, index) => (
                      <SkillPill key={index} skill={skill} />
                    ))}
                  </div>
                </div>
              )}

              {normalizedJD.experience && (
                <div className="bg-surface-container-low p-sm rounded-xl border border-outline-variant">
                  <span className="text-[10px] uppercase tracking-wider text-outline block font-label-caps font-semibold">Experience Requirement</span>
                  <span className="text-on-surface font-semibold text-sm">{normalizedJD.experience} Years</span>
                </div>
              )}
            </Card>
          ) : (
            <Card variant="raised" className="h-full flex flex-col items-center justify-center text-center p-xl opacity-60">
              <span className="material-symbols-outlined text-6xl text-outline mb-md">rule</span>
              <h3 className="font-h3 text-on-surface font-semibold mb-xs">No JD Normalized</h3>
              <p className="text-sm text-outline max-w-[320px]">
                Paste a messy raw JD description on the left panel to automatically extract clean normalized keywords.
              </p>
            </Card>
          )}
        </div>
      </div>

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
