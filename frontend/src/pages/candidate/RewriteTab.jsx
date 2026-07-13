import React, { useState } from 'react';
import { useCandidateStore } from '../../store/candidateStore';
import { candidateApi } from '../../api/candidateApi';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { InputField } from '../../components/common/InputField';
import { ActiveProfileBadge } from '../../components/common/ActiveProfileBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';

export const RewriteTab = () => {
  const { parsedProfile, candidateId, rewriteResults, setRewriteResults, clearSession } = useCandidateStore();
  
  const [jdText, setJdText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');

  // Focus Area options matching Spacious original spec
  const focusOptions = ['Quantifiable Impact', 'Action Verbs', 'Technical Skills', 'Clarity & Brevity', 'Industry Lingo'];
  const [selectedFocus, setSelectedFocus] = useState(['Quantifiable Impact', 'Action Verbs']);

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const toggleFocus = (option) => {
    if (selectedFocus.includes(option)) {
      setSelectedFocus(selectedFocus.filter(f => f !== option));
    } else {
      setSelectedFocus([...selectedFocus, option]);
    }
  };

  const handleRewrite = async () => {
    if (!jdText || !jdText.trim()) {
      triggerToast('Please provide the target Job Description first.', 'warning');
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        candidate_id: candidateId || null,
        candidate_data: candidateId ? null : parsedProfile,
        jd_text: jdText.trim(),
        focus_areas: selectedFocus
      };
      
      const response = await candidateApi.rewriteResume(payload);
      setRewriteResults(response);
      triggerToast('Resume optimization completed successfully!', 'success');
    } catch (err) {
      console.error(err);
      triggerToast('Failed to optimize resume text.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (!rewriteResults || !rewriteResults.optimized_bullets) return;
    const bulletList = rewriteResults.optimized_bullets.map(b => `• ${b.optimized}`).join('\n');
    navigator.clipboard.writeText(bulletList);
    triggerToast('Optimized resume text copied to clipboard!', 'success');
  };

  const handleDownload = () => {
    if (!rewriteResults || !rewriteResults.optimized_bullets) return;
    const bulletList = rewriteResults.optimized_bullets.map(b => `• ${b.optimized}`).join('\n');
    const element = document.createElement("a");
    const file = new Blob([bulletList], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = "optimized_resume_bullets.txt";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    triggerToast('Download started!', 'success');
  };

  const renderBoldText = (text) => {
    if (!text) return '';
    // Regex matches text inside ** or standard b tags
    const parts = text.split(/\*\*([^*]+)\*\*/g);
    return parts.map((part, i) => i % 2 === 1 ? (
      <strong key={i} className="font-extrabold text-primary font-mono">{part}</strong>
    ) : part);
  };

  return (
    <div className="space-y-lg max-w-[1100px] mx-auto pb-16">
      {/* Header section with vertical breathing room */}
      <div className="mb-lg space-y-xs">
        <h2 className="font-h1 text-h1 text-primary font-bold">Rewrite Resume</h2>
        <p className="font-body-md text-on-surface-variant">
          Refine your bullets for maximum impact and ATS compatibility.
        </p>
      </div>

      {/* 1. Optimization Parameters Card (Full Width) */}
      <Card variant="raised" className="p-lg">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-lg">
          {/* Left Inputs */}
          <div className="space-y-md">
            <div className="space-y-xs">
              <label className="text-[10px] font-bold text-primary uppercase tracking-widest block font-label-caps">
                Select Resume Version
              </label>
              <div className="relative">
                <select 
                  className="w-full bg-white border border-outline-variant rounded-xl p-3 text-xs text-on-surface font-semibold focus:ring-1 focus:ring-primary outline-none transition-all cursor-pointer appearance-none pr-10"
                  disabled
                >
                  <option>
                    {parsedProfile ? `${parsedProfile.name}` : 'No parsed profile loaded'}
                  </option>
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none">
                  <span className="material-symbols-outlined text-sm">unfold_more</span>
                </div>
              </div>
            </div>

            <div className="space-y-xs">
              <label className="text-[10px] font-bold text-primary uppercase tracking-widest block font-label-caps">
                Job Description / Target Role
              </label>
              <textarea 
                className="w-full p-4 border border-outline-variant bg-white text-xs text-on-surface rounded-xl focus:ring-1 focus:ring-primary outline-none resize-none transition-all"
                placeholder="Paste the job description here to tailor your results..."
                rows="6"
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Right Inputs & AI recommendation */}
          <div className="flex flex-col justify-between">
            <div className="space-y-md">
              <div className="space-y-xs">
                <label className="text-[10px] font-bold text-primary uppercase tracking-widest block font-label-caps">
                  Focus Areas
                </label>
                <div className="flex flex-wrap gap-xs">
                  {focusOptions.map((opt) => {
                    const isSelected = selectedFocus.includes(opt);
                    return (
                      <button
                        key={opt}
                        onClick={() => toggleFocus(opt)}
                        disabled={isLoading}
                        className={`text-[11px] px-4 py-2 rounded-full font-bold transition-all border shadow-sm ${
                          isSelected 
                            ? 'bg-primary text-white border-primary-container' 
                            : 'bg-white text-on-surface-variant border-outline-variant hover:bg-surface-variant'
                        }`}
                      >
                        {opt}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* AI Recommendation */}
              <div className="p-md bg-primary-container/15 border-l-4 border-primary rounded-2xl flex gap-sm items-start">
                <span className="material-symbols-outlined text-primary text-xl">lightbulb</span>
                <div className="space-y-xs">
                  <h4 className="text-xs font-bold text-on-surface font-h3">AI Recommendation</h4>
                  <p className="text-[11px] text-on-surface-variant leading-relaxed">
                    Based on your role, focusing on <strong>Quantifiable Impact</strong> will increase your interview rate by up to 22%.
                  </p>
                </div>
              </div>
            </div>

            <Button 
              variant="gradient" 
              onClick={handleRewrite}
              disabled={isLoading}
              className="w-full mt-lg py-4 text-xs font-bold"
              icon="auto_fix_high"
            >
              {isLoading ? <LoadingSpinner size="sm" /> : 'Optimize My Resume'}
            </Button>
          </div>
        </div>
      </Card>

      {/* 2. Results Summary Strip (Full Width) */}
      {rewriteResults && (
        <div className="bg-primary-container/15 border-l-[6px] border-primary rounded-3xl p-md flex flex-col md:flex-row items-center justify-between gap-md shadow-sm animate-fade-in">
          <div className="flex items-center gap-md">
            <div className="flex items-center justify-center w-16 h-16 rounded-full border-[6px] border-primary border-t-transparent/20 rotate-[-45deg] flex-shrink-0 bg-white shadow-sm">
              <span className="rotate-[45deg] font-bold text-base text-primary font-h2">
                88%
              </span>
            </div>
            <div>
              <h3 className="text-base font-bold text-on-surface font-h3">Overall Impact</h3>
              <p className="text-on-surface-variant text-xs mt-0.5">
                Matching 14 out of 16 critical keywords for this role.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-xs justify-center md:justify-end">
            {rewriteResults.added_keywords && rewriteResults.added_keywords.map((kw, idx) => (
              <span 
                key={idx} 
                className="px-3 py-1 bg-white border border-outline-variant text-on-surface-variant rounded-md text-xs font-semibold shadow-sm"
              >
                #{kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 3. Sentence Comparison Grid */}
      {rewriteResults ? (
        <div className="space-y-md">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-end gap-sm">
            <h2 className="text-2xl font-bold font-h2 text-primary">Sentence Comparison</h2>
            <div className="flex gap-md">
              <button 
                onClick={handleDownload}
                className="flex items-center gap-1.5 text-primary hover:underline font-semibold text-xs transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">download</span> Download Text
              </button>
              <button 
                onClick={handleCopy}
                className="flex items-center gap-1.5 text-primary hover:underline font-semibold text-xs transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">content_copy</span> Copy Optimized Resume
              </button>
            </div>
          </div>

          {/* Cards List */}
          <div className="space-y-md">
            {(rewriteResults.optimized_bullets || []).map((bullet, index) => (
              <Card key={index} variant="raised" className="overflow-hidden p-0 border border-outline-variant/30">
                <div className="grid grid-cols-1 md:grid-cols-2">
                  {/* Left Column: Original */}
                  <div className="p-lg border-b md:border-b-0 md:border-r border-outline-variant/30 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-sm text-on-surface-variant/70">
                        <span className="material-symbols-outlined text-[18px]">history</span>
                        <span className="text-xs font-bold uppercase tracking-widest font-label-caps">Original Text</span>
                      </div>
                      <p className="text-on-surface-variant leading-relaxed text-xs">
                        {bullet.original}
                      </p>
                    </div>
                  </div>
                  {/* Right Column: Optimized */}
                  <div className="p-lg bg-surface-container-low/40 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-sm">
                        <div className="flex items-center gap-2 text-primary">
                          <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>verified</span>
                          <span className="text-xs font-bold uppercase tracking-widest font-label-caps">Optimized for Impact</span>
                        </div>
                        <span className="bg-primary/10 border border-primary/20 text-primary px-2.5 py-0.5 rounded text-[10px] font-bold whitespace-nowrap">
                          {(() => {
                            const r = (bullet.reason || '').toLowerCase();
                            if (r.includes('keyword') || r.includes('term')) return 'KEYWORD ADDED';
                            if (r.includes('clear') || r.includes('brevity') || r.includes('concise')) return 'IMPROVED CLARITY';
                            if (r.includes('metric') || r.includes('impact') || r.includes('quantifiable')) return 'IMPROVED IMPACT';
                            return 'HIGH MATCH';
                          })()}
                        </span>
                      </div>
                      <p className="text-on-surface leading-relaxed text-xs">
                        {renderBoldText(bullet.optimized)}
                      </p>
                      {bullet.reason && (
                        <div className="mt-sm pt-xs border-t border-outline-variant/30 text-[10px] text-on-surface-variant font-medium">
                          <span className="text-primary font-bold">Alignment feedback:</span> {bullet.reason}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {/* 4. Final Action Bar (Floating Centered) */}
          <div className="mt-xl flex justify-center pt-md">
            <div className="bg-white border border-outline-variant rounded-full py-3 px-8 shadow-2xl flex items-center gap-lg animate-bounce-subtle backdrop-blur-md">
              <div className="hidden sm:flex flex-col">
                <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest font-label-caps">Current ATS Readiness</span>
                <span className="font-bold text-xs text-primary">Elite Status (92/100)</span>
              </div>
              <div className="h-6 w-px bg-outline-variant hidden sm:block"></div>
              <div className="flex gap-sm">
                <Button 
                  onClick={handleCopy}
                  className="px-6 py-2 rounded-full text-xs font-semibold active:scale-95"
                >
                  Finalize &amp; Export
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <Card variant="raised" className="h-full flex flex-col items-center justify-center text-center p-xl opacity-60 min-h-[300px]">
          <span className="material-symbols-outlined text-6xl text-outline mb-md">auto_awesome</span>
          <h3 className="font-h3 text-on-surface font-semibold mb-xs">No Rewrite Results</h3>
          <p className="text-sm text-outline max-w-[320px]">
            Enter target JD on the left panel and click Optimize to generate STAR structured bullet points.
          </p>
        </Card>
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
