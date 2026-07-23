import React, { useState } from 'react';
import { useCandidateStore } from '../../store/candidateStore';
import { candidateApi } from '../../api/candidateApi';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { InputField } from '../../components/common/InputField';
import { ActiveProfileBadge } from '../../components/common/ActiveProfileBadge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';
import { TargetRoleSection } from './components/TargetRoleSection';
import { AnalysisResultsDashboard } from './components/AnalysisResultsDashboard';

// Compute score tier from evaluation score
const getScoreTier = (score) => {
  if (score === null || score === undefined) return null;
  if (score < 30) return 'FUNDAMENTALS';
  if (score < 60) return 'BASIC';
  if (score < 80) return 'GAP_ANALYSIS';
  return 'ADVANCED';
};

const TIER_CONFIG = {
  FUNDAMENTALS: {
    label: 'Focus on Fundamentals',
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: 'school',
    description: 'Your score is below 30. The mock interview requires a minimum foundation. Study the core concepts listed in your gaps first.',
    canStart: false,
  },
  BASIC: {
    label: 'Basic Confidence Round',
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: 'emoji_objects',
    description: '5 foundational questions to build your confidence on known skills. No advanced round.',
    canStart: true,
  },
  GAP_ANALYSIS: {
    label: 'Gap Analysis Round',
    color: 'text-blue-700',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: 'analytics',
    description: '5 targeted questions addressing your identified skill gaps. Advanced round unlocks if your avg score >= 70.',
    canStart: true,
  },
  ADVANCED: {
    label: 'Advanced Preparation',
    color: 'text-purple-700',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    icon: 'rocket_launch',
    description: '5 expert-level system design & architecture questions. Advanced round automatically offered at the end.',
    canStart: true,
  },
};

export const EvaluationTab = () => {
  const { parsedProfile, candidateId, evaluationResult, setEvaluationResult, clearSession } = useCandidateStore();
  
  const [jobId, setJobId] = useState('');
  const [jdText, setJdText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');
  
  // Modals for all strengths/gaps
  const [showAllStrengths, setShowAllStrengths] = useState(false);
  const [showAllGaps, setShowAllGaps] = useState(false);

  // Interactive Interview Simulator States
  // States: 'NOT_STARTED', 'IN_PROGRESS', 'UPGRADE_PROMPT', 'COMPLETED'
  const [interviewState, setInterviewState] = useState('NOT_STARTED');
  const [isStartingInterview, setIsStartingInterview] = useState(false);
  const [activeQuestion, setActiveQuestion] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  
  const [lastFeedback, setLastFeedback] = useState(null);
  const [history, setHistory] = useState([]);
  const [isAdvanced, setIsAdvanced] = useState(false);
  const [averageScore, setAverageScore] = useState(0.0);
  const [finalReport, setFinalReport] = useState(null);
  const [basicReport, setBasicReport] = useState(null);
  const [showBasicReport, setShowBasicReport] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [scoreTier, setScoreTier] = useState(null);

  const triggerToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  };

  const handleEvaluate = async () => {
    if (!jdText || !jdText.trim()) {
      triggerToast('Please provide a Job Description.', 'warning');
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        candidate_id: candidateId || null,
        candidate_data: candidateId ? null : parsedProfile,
        jd_text: jdText.trim()
      };
      
      const response = await candidateApi.selfEvaluate(payload);
      setEvaluationResult(response);
      const tier = getScoreTier(response.score_100);
      setScoreTier(tier);

      // Reset interview simulator
      setInterviewState('NOT_STARTED');
      setActiveQuestion(null);
      setLastFeedback(null);
      setHistory([]);
      setIsAdvanced(false);
      setSessionId(null);
      setFinalReport(null);
      setBasicReport(null);
      setShowBasicReport(false);
      setUserAnswer('');

      triggerToast(`AI Evaluation complete! Fit Score: ${response.score_100}% — ${TIER_CONFIG[tier]?.label || tier}`, 'success');
    } catch (err) {
      console.error(err);
      triggerToast('Evaluation failed. Please try again.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartInterview = async () => {
    if (!evaluationResult) return;
    const tier = scoreTier || getScoreTier(evaluationResult.score_100);
    if (tier === 'FUNDAMENTALS') {
      triggerToast('Score too low for mock interview. Study the fundamentals first.', 'error');
      return;
    }
    setIsStartingInterview(true);
    try {
      const payload = {
        candidate_id: candidateId,
        candidate_data: candidateId ? null : parsedProfile,
        jd_text: jdText.trim(),
        gaps: evaluationResult.gaps || [],
        evaluation_score: evaluationResult.score_100,
        score_tier: tier
      };
      const response = await candidateApi.startInterview(payload);
      if (response.status === 'success') {
        setSessionId(response.session_id);
        setScoreTier(response.score_tier || tier);
        setActiveQuestion({
          question_text: response.question_text,
          difficulty_level: response.difficulty_level
        });
        setInterviewState('IN_PROGRESS');
        setHistory([]);
        setLastFeedback(null);
        setIsAdvanced(false);
        setFinalReport(null);
        setBasicReport(null);
        setShowBasicReport(false);
        setUserAnswer('');
        triggerToast('Mock Interview started! Here is your first question.', 'success');
      } else {
        triggerToast('Failed to start interview round.', 'error');
      }
    } catch (err) {
      const errDetail = err?.response?.data?.detail || err?.message || 'Unknown error';
      console.error('[Interview Start Error]', errDetail, err);
      triggerToast(`Failed to connect to interview server: ${errDetail}`, 'error');
    } finally {
      setIsStartingInterview(false);
    }
  };


  const handleAnswerSubmit = async () => {
    if (!userAnswer || !userAnswer.trim()) {
      triggerToast('Please type your response.', 'warning');
      return;
    }

    setIsSubmittingAnswer(true);
    try {
      const payload = {
        session_id: sessionId,
        candidate_id: candidateId,
        candidate_data: candidateId ? null : parsedProfile,
        jd_text: jdText.trim(),
        gaps: evaluationResult.gaps || [],
        question_text: activeQuestion.question_text,
        answer_text: userAnswer.trim(),
        difficulty_level: activeQuestion.difficulty_level,
        history: history,
        is_advanced: isAdvanced,
        score_tier: scoreTier
      };

      const response = await candidateApi.submitInterviewAnswer(payload);
      
      setLastFeedback({
        answer_score: response.answer_score,
        feedback: response.feedback,
        strengths: response.strengths,
        weaknesses: response.weaknesses,
        difficulty_level: activeQuestion.difficulty_level,
        next_difficulty: response.next_question?.difficulty_level || 'same'
      });

      setHistory(response.history);
      setAverageScore(response.average_score);

      if (response.status === 'UPGRADE_PROMPT') {
        setBasicReport(response.basic_report || null);
        setInterviewState('UPGRADE_PROMPT');
      } else if (response.status === 'COMPLETED') {
        setInterviewState('COMPLETED');
        setFinalReport(response.final_report);
        triggerToast('Interview completed! Generating final report...', 'success');
      } else {
        // IN_PROGRESS: Stage the next question
        setActiveQuestion({
          question_text: response.next_question.question_text,
          difficulty_level: response.next_question.difficulty_level
        });
      }
    } catch (err) {
      console.error(err);
      triggerToast('Failed to grade answer. Please try again.', 'error');
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleAcceptUpgrade = async (accept) => {
    if (accept) {
      setIsSubmittingAnswer(true);
      setShowBasicReport(false);
      try {
        const payload = {
          session_id: sessionId,
          candidate_id: candidateId,
          candidate_data: candidateId ? null : parsedProfile,
          jd_text: jdText.trim(),
          gaps: evaluationResult.gaps || [],
          question_text: "Initiate Advanced scenarios",
          answer_text: "Let's proceed",
          difficulty_level: "HARD",
          history: history,
          is_advanced: true,
          score_tier: scoreTier
        };
        const response = await candidateApi.submitInterviewAnswer(payload);
        
        setIsAdvanced(true);
        setInterviewState('IN_PROGRESS');
        setUserAnswer('');
        setLastFeedback(null);
        setActiveQuestion({
          question_text: response.next_question.question_text,
          difficulty_level: response.next_question.difficulty_level
        });
        triggerToast('Advanced round activated! 3 system-design questions incoming.', 'success');
      } catch (err) {
        console.error(err);
        triggerToast('Failed to start advanced round.', 'error');
      } finally {
        setIsSubmittingAnswer(false);
      }
    } else {
      // Candidate chose "Finish Mock" — use already-generated basic_report
      if (basicReport) {
        setFinalReport(basicReport);
        setInterviewState('COMPLETED');
        triggerToast('Interview completed. Your 5-question report is ready!', 'success');
        return;
      }
      // Fallback: fetch from backend if basicReport not cached
      setIsSubmittingAnswer(true);
      try {
        const response = await candidateApi.submitInterviewAnswer({
          session_id: sessionId,
          candidate_id: candidateId,
          candidate_data: candidateId ? null : parsedProfile,
          jd_text: jdText.trim(),
          gaps: evaluationResult.gaps || [],
          question_text: "Complete mock session",
          answer_text: "Show final report",
          difficulty_level: activeQuestion?.difficulty_level || 'MEDIUM',
          is_advanced: false,
          history: history,
          score_tier: scoreTier
        });
        setInterviewState('COMPLETED');
        setFinalReport(response.final_report);
        triggerToast('Interview completed successfully.', 'success');
      } catch (err) {
        console.error(err);
        triggerToast('Failed to generate final report.', 'error');
      } finally {
        setIsSubmittingAnswer(false);
      }
    }
  };

  const handleContinueNext = () => {
    setUserAnswer('');
    setLastFeedback(null);
  };

  return (
    <div className="space-y-xl max-w-[1100px] mx-auto pb-16">
      <TargetRoleSection
        jdText={jdText}
        setJdText={setJdText}
        isLoading={isLoading}
        interviewState={interviewState}
        clearSession={clearSession}
        handleEvaluate={handleEvaluate}
      />

      <AnalysisResultsDashboard
        evaluationResult={evaluationResult}
        scoreTier={scoreTier}
        TIER_CONFIG={TIER_CONFIG}
        interviewState={interviewState}
        handleStartInterview={handleStartInterview}
        isStartingInterview={isStartingInterview}
        setShowAllStrengths={setShowAllStrengths}
        setShowAllGaps={setShowAllGaps}
      />

      {/* Step 5: Practice Area (Full Width Mock Interview Panels) */}
      {interviewState === 'IN_PROGRESS' && activeQuestion && (
        <section className="space-y-lg animate-fade-in">
          <div className="flex items-center gap-3 mb-sm">
            <span className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold font-h2">3</span>
            <h2 className="text-2xl font-bold font-h2 text-primary">Interview Practice</h2>
          </div>

          <div className="space-y-md">
            {/* Question Card */}
            <Card variant="raised" className="p-lg border-l-4 border-primary">
              <div className="space-y-md">
                <div className="flex items-center justify-between border-b border-outline-variant/30 pb-xs">
                  <span className="text-xs font-bold text-primary uppercase tracking-wider font-label-caps">
                    Round Progress: {history.length + 1} of {isAdvanced ? '8' : '5'}
                  </span>
                  <span className="text-xs text-on-surface-variant font-medium">
                    {isAdvanced ? 'Advanced Round' : 'Initial Round'} • {activeQuestion.difficulty_level}
                  </span>
                </div>
                
                <h3 className="text-lg font-bold text-on-surface font-h3 leading-relaxed">
                  "{activeQuestion.question_text}"
                </h3>

                <div className="space-y-sm pt-xs">
                  <textarea 
                    className="w-full px-4 py-3 rounded-xl border border-outline-variant bg-white text-xs text-on-surface leading-relaxed focus:ring-1 focus:ring-primary outline-none resize-none transition-all"
                    placeholder="Your answer (The STAR method is recommended)..."
                    rows="6"
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    disabled={isSubmittingAnswer || lastFeedback !== null}
                  />
                  
                  {!lastFeedback && (
                    <div className="flex justify-end">
                      <Button 
                        variant="gradient" 
                        onClick={handleAnswerSubmit}
                        disabled={isSubmittingAnswer || !userAnswer.trim()}
                        className="px-8 py-2.5 rounded-full text-xs font-semibold"
                      >
                        {isSubmittingAnswer ? <LoadingSpinner size="sm" /> : 'Submit Answer'}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* Combined Feedback Card */}
            {lastFeedback && (
              <Card variant="raised" className="overflow-hidden p-0 border border-outline-variant/30 animate-slide-in">
                <div className="p-lg">
                  <div className="flex flex-col md:flex-row gap-lg">
                    {/* Score */}
                    <div className="md:w-1/4 flex flex-col items-center justify-center text-center border-b md:border-b-0 md:border-r border-outline-variant/30 pb-md md:pb-0">
                      <div className="text-5xl font-extrabold text-primary font-h1">{lastFeedback.answer_score}</div>
                      <div className="text-[10px] font-bold text-outline uppercase tracking-widest mt-1 font-label-caps">AI SCORE</div>
                      <div className="mt-4 w-full max-w-[120px] h-2 bg-surface-container-high rounded-full overflow-hidden border border-outline-variant/35">
                        <div 
                          className="bg-primary h-full rounded-full transition-all duration-500" 
                          style={{ width: `${lastFeedback.answer_score}%` }}
                        />
                      </div>
                    </div>

                    {/* Feedback List */}
                    <div className="md:w-3/4 space-y-md">
                      <h4 className="text-base font-bold text-on-surface font-h3">Analysis Feedback</h4>
                      
                      <ul className="space-y-sm">
                        <li className="flex gap-3 items-start">
                          <span className="material-symbols-outlined text-green-600 mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                          <div className="space-y-xs">
                            <p className="font-bold text-on-surface text-xs">Response Rating & Feedback</p>
                            <p className="text-on-surface-variant text-xs leading-relaxed">{lastFeedback.feedback}</p>
                          </div>
                        </li>

                        {lastFeedback.strengths && lastFeedback.strengths.length > 0 && (
                          <li className="flex gap-3 items-start">
                            <span className="material-symbols-outlined text-green-600 mt-0.5">thumb_up</span>
                            <div className="space-y-xs">
                              <p className="font-bold text-on-surface text-xs">Technical Strengths</p>
                              <p className="text-on-surface-variant text-xs leading-relaxed">
                                {lastFeedback.strengths.join(', ')}
                              </p>
                            </div>
                          </li>
                        )}

                        {lastFeedback.weaknesses && lastFeedback.weaknesses.length > 0 && (
                          <li className="flex gap-3 items-start">
                            <span className="material-symbols-outlined text-amber-600 mt-0.5">lightbulb</span>
                            <div className="space-y-xs">
                              <p className="font-bold text-on-surface text-xs">Improvement Suggestions</p>
                              <p className="text-on-surface-variant text-xs leading-relaxed">
                                {lastFeedback.weaknesses.join(', ')}
                              </p>
                            </div>
                          </li>
                        )}
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Continue Action */}
                <div className="bg-surface-container-low/40 border-t border-outline-variant/30 p-4 px-lg flex justify-center">
                  <Button 
                    variant="ghost" 
                    onClick={handleContinueNext} 
                    className="px-10 py-2.5 rounded-full text-xs font-bold"
                  >
                    Continue to Next Question
                  </Button>
                </div>
              </Card>
            )}
          </div>
        </section>
      )}

      {/* Upgrade Prompt Screen */}
      {interviewState === 'UPGRADE_PROMPT' && (
        <div className="space-y-md max-w-[750px] mx-auto animate-fade-in">
          {/* Score banner */}
          <Card variant="raised" className="relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-green-500/10 pointer-events-none" />
            <div className="p-lg flex flex-col items-center text-center gap-sm relative">
              <div className="w-16 h-16 bg-green-50 text-green-700 rounded-full flex items-center justify-center animate-bounce border-2 border-green-300 shadow-md">
                <span className="material-symbols-outlined text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>workspace_premium</span>
              </div>
              <h3 className="text-xl font-bold font-h2 text-on-surface">Initial Round Complete!</h3>
              <div className="flex flex-wrap items-center justify-center gap-sm">
                <span className="bg-primary text-white px-5 py-1.5 rounded-full text-sm font-bold shadow">
                  Average Score: {averageScore}%
                </span>
                <span className="bg-green-100 text-green-800 border border-green-300 px-4 py-1.5 rounded-full text-xs font-semibold">
                  ✓ Eligible for Advanced Round
                </span>
              </div>
              <p className="text-xs text-on-surface-variant max-w-[420px] leading-relaxed">
                Your score qualifies you for the <strong>Advanced Round</strong> — 3 system-design questions that test deeper expertise.
                You can view your 5-question report below before deciding.
              </p>
            </div>
          </Card>

          {/* View 5-Q Report toggle */}
          {basicReport && (
            <div className="space-y-sm">
              <button
                onClick={() => setShowBasicReport(v => !v)}
                className="w-full flex items-center justify-between bg-surface-container border border-outline-variant rounded-2xl px-md py-sm hover:bg-surface-container-high transition-colors group"
              >
                <span className="flex items-center gap-xs text-sm font-bold text-primary">
                  <span className="material-symbols-outlined text-base">description</span>
                  View Your 5-Question Report
                </span>
                <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors">
                  {showBasicReport ? 'expand_less' : 'expand_more'}
                </span>
              </button>

              {showBasicReport && (
                <Card variant="inset" className="p-md space-y-md animate-fade-in border border-primary/20">
                  <div className="bg-primary/5 p-sm rounded-xl border border-primary/15 space-y-xs">
                    <span className="text-[10px] font-bold text-primary uppercase tracking-wider block">Confidence Feedback</span>
                    <p className="text-xs text-on-surface-variant leading-relaxed">{basicReport.confidence_feedback}</p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-sm">
                    <div className="bg-green-50/60 p-sm rounded-xl border border-green-200/60 space-y-xs">
                      <h4 className="text-xs font-bold text-green-900 flex items-center gap-1">
                        <span className="material-symbols-outlined text-green-700 text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>thumb_up</span>
                        Strengths
                      </h4>
                      <ul className="space-y-1">
                        {(basicReport.strengths || []).map((s, i) => (
                          <li key={i} className="text-[11px] text-green-800 flex items-start gap-1"><span className="text-green-600 mt-0.5">✓</span>{s}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="bg-orange-50/60 p-sm rounded-xl border border-orange-200/60 space-y-xs">
                      <h4 className="text-xs font-bold text-orange-900 flex items-center gap-1">
                        <span className="material-symbols-outlined text-amber-700 text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>lightbulb</span>
                        Gaps & Suggestions
                      </h4>
                      <ul className="space-y-1">
                        {(basicReport.suggestions || []).map((s, i) => (
                          <li key={i} className="text-[11px] text-orange-800 flex items-start gap-1"><span className="text-amber-600 mt-0.5">→</span>{s}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Action buttons */}
          <Card variant="raised" className="p-md">
            <div className="flex flex-col sm:flex-row gap-sm items-center justify-between">
              <div className="text-xs text-on-surface-variant space-y-0.5">
                <p className="font-semibold text-on-surface">Ready for Advanced Round?</p>
                <p>3 harder system-design questions. A combined 8-question report will be generated.</p>
              </div>
              <div className="flex gap-sm shrink-0">
                <Button
                  variant="ghost"
                  onClick={() => handleAcceptUpgrade(false)}
                  disabled={isSubmittingAnswer}
                  className="text-xs px-6"
                >
                  Finish with 5-Q Report
                </Button>
                <Button
                  variant="gradient"
                  onClick={() => handleAcceptUpgrade(true)}
                  disabled={isSubmittingAnswer}
                  className="text-xs px-6"
                >
                  {isSubmittingAnswer ? <LoadingSpinner size="sm" /> : '⚡ Start Advanced Round'}
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Completed Final Report Modal Screen */}
      {interviewState === 'COMPLETED' && finalReport && (
        <div className="fixed inset-0 bg-[#0f172a]/70 backdrop-blur-md z-50 flex items-center justify-center p-md overflow-y-auto animate-fade-in">
          <div className="bg-surface max-w-[850px] w-full rounded-3xl border border-outline-variant/60 shadow-2xl overflow-hidden animate-scale-in max-h-[90vh] flex flex-col">
            {/* Header: Premium colorful gradient background */}
            <div className="bg-gradient-to-r from-primary to-primary-container p-lg flex justify-between items-center text-white">
              <div className="flex items-center gap-base">
                <span className="material-symbols-outlined text-3xl text-yellow-300 animate-pulse" style={{ fontVariationSettings: "'FILL' 1" }}>emoji_events</span>
                <div>
                  <h3 className="text-xl font-bold font-h2">
                    {finalReport?.report_type === 'combined' ? 'Combined Mock Interview Report (8 Questions)' : 'Mock Interview Final Report'}
                  </h3>
                  <p className="text-[11px] text-white/80">
                    {finalReport?.report_type === 'combined'
                      ? '5 initial + 3 advanced questions — comprehensive technical performance review'
                      : 'Detailed technical performance review and development suggestions'}
                  </p>
                </div>
              </div>
              <div className="bg-white/20 backdrop-blur-md border border-white/30 text-white px-5 py-2 rounded-full text-sm font-bold shadow-md">
                Average Score: {finalReport.average_score}%
              </div>
            </div>

            {/* Modal Content Body */}
            <div className="p-lg overflow-y-auto space-y-lg flex-1 custom-scrollbar">
              {/* Confidence Feedback */}
              <div className="bg-primary/5 p-md rounded-2xl border border-primary/20 space-y-xs">
                <span className="text-[10px] text-primary font-bold tracking-wider uppercase block font-label-caps">Confidence Feedback</span>
                <p className="text-xs text-on-surface-variant font-medium leading-relaxed">
                  {finalReport.confidence_feedback}
                </p>
              </div>

              {/* Strengths & Suggestions side-by-side grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
                {/* Strengths */}
                <div className="bg-green-50/50 p-md rounded-2xl border border-green-200/60 space-y-sm">
                  <h4 className="text-sm font-bold text-green-950 flex items-center gap-xs font-h3 border-b border-green-200 pb-xs">
                    <span className="material-symbols-outlined text-green-700" style={{ fontVariationSettings: "'FILL' 1" }}>thumb_up</span>
                    Consolidated Strengths
                  </h4>
                  <ul className="space-y-xs">
                    {finalReport.strengths && finalReport.strengths.length > 0 ? (
                      finalReport.strengths.map((str, sIdx) => (
                        <li key={sIdx} className="bg-white p-2.5 rounded-xl border border-green-100 text-xs text-green-900 flex items-start gap-xs shadow-sm font-medium">
                          <span className="material-symbols-outlined text-green-600 text-sm mt-0.5">check</span>
                          {str}
                        </li>
                      ))
                    ) : (
                      <li className="text-xs text-green-800 italic">No specific strengths listed.</li>
                    )}
                  </ul>
                </div>

                {/* Suggestions */}
                <div className="bg-orange-50/50 p-md rounded-2xl border border-orange-200/60 space-y-sm">
                  <h4 className="text-sm font-bold text-orange-950 flex items-center gap-xs font-h3 border-b border-orange-200 pb-xs">
                    <span className="material-symbols-outlined text-amber-700" style={{ fontVariationSettings: "'FILL' 1" }}>lightbulb</span>
                    Actionable Gaps & Suggestions
                  </h4>
                  <ul className="space-y-xs">
                    {finalReport.suggestions && finalReport.suggestions.length > 0 ? (
                      finalReport.suggestions.map((sug, sIdx) => (
                        <li key={sIdx} className="bg-white p-2.5 rounded-xl border border-orange-100 text-xs text-orange-900 flex items-start gap-xs shadow-sm font-medium">
                          <span className="material-symbols-outlined text-amber-600 text-sm mt-0.5">arrow_right_alt</span>
                          {sug}
                        </li>
                      ))
                    ) : (
                      <li className="text-xs text-orange-800 italic">No specific improvement suggestions listed.</li>
                    )}
                  </ul>
                </div>
              </div>

              {/* Detailed Q&A Review History list */}
              <div className="space-y-md border-t border-outline-variant/40 pt-md">
                <h4 className="text-sm font-bold text-on-surface font-h3 flex items-center gap-xs">
                  <span className="material-symbols-outlined text-primary">menu_book</span>
                  Question & Answer Review ({history.length} answered)
                </h4>
                
                <div className="space-y-md">
                  {history.map((hItem, idx) => (
                    <Card key={idx} variant="inset" className="p-md space-y-sm border border-outline-variant/35 relative overflow-hidden bg-white/60">
                      {/* Q&A Order and Difficulty */}
                      <div className="flex justify-between items-center border-b border-outline-variant/20 pb-2">
                        <span className="text-xs font-bold text-primary font-label-caps">
                          Question {idx + 1}
                        </span>
                        <div className="flex items-center gap-xs">
                          <span className="bg-primary/10 border border-primary/20 text-primary px-2.5 py-0.5 rounded text-[10px] font-bold">
                            {hItem.difficulty_level || 'MEDIUM'}
                          </span>
                          <span className="bg-primary text-white px-2.5 py-0.5 rounded text-[10px] font-bold shadow-sm">
                            SCORE: {hItem.answer_score}/100
                          </span>
                        </div>
                      </div>

                      {/* Question Text */}
                      <div className="space-y-xs">
                        <span className="text-[9px] uppercase tracking-wider text-outline font-bold block font-label-caps">QUESTION</span>
                        <p className="text-xs text-on-surface font-semibold italic">"{hItem.question_text}"</p>
                      </div>

                      {/* Answer Text */}
                      <div className="space-y-xs bg-surface-container-low/40 p-sm rounded-xl border border-outline-variant/25">
                        <span className="text-[9px] uppercase tracking-wider text-outline font-bold block font-label-caps font-semibold">YOUR RESPONSE</span>
                        <p className="text-xs text-on-surface-variant leading-relaxed whitespace-pre-line font-medium">
                          {hItem.answer_text}
                        </p>
                      </div>

                      {/* AI Evaluation Feedback */}
                      <div className="space-y-xs border-t border-outline-variant/20 pt-sm">
                        <span className="text-[9px] uppercase tracking-wider text-primary font-bold block font-label-caps">AI EVALUATION FEEDBACK</span>
                        <p className="text-xs text-on-surface leading-relaxed font-semibold">
                          {hItem.feedback}
                        </p>
                      </div>

                      {/* Individual strengths/weaknesses if present */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-sm pt-xs">
                        {hItem.strengths && hItem.strengths.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[9px] uppercase tracking-wider text-green-700 font-bold block font-label-caps">Strengths</span>
                            <div className="flex flex-wrap gap-1">
                              {hItem.strengths.map((str, sIdx) => (
                                <span key={sIdx} className="bg-green-50/75 text-green-800 border border-green-200/50 px-2 py-0.5 rounded text-[10px] font-medium leading-tight">
                                  ✓ {str}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {hItem.weaknesses && hItem.weaknesses.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[9px] uppercase tracking-wider text-amber-700 font-bold block font-label-caps">Weaknesses</span>
                            <div className="flex flex-wrap gap-1">
                              {hItem.weaknesses.map((wk, wIdx) => (
                                <span key={wIdx} className="bg-orange-50/75 text-primary-container border border-orange-200/50 px-2 py-0.5 rounded text-[10px] font-medium leading-tight">
                                  ✗ {wk}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="bg-surface-container-low border-t border-outline-variant/40 p-md flex justify-between items-center">
              <Button variant="ghost" onClick={() => setInterviewState('NOT_STARTED')} className="text-xs px-6 py-2.5">
                Back to Summary
              </Button>
              <Button variant="gradient" onClick={handleStartInterview} className="text-xs px-6 py-2.5">
                Retry Mock Interview
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Strengths View All Modal */}
      {showAllStrengths && evaluationResult && (
        <div className="fixed inset-0 bg-surface/80 backdrop-blur-sm z-50 flex items-center justify-center p-md animate-fade-in">
          <div className="bg-surface max-w-[500px] w-full rounded-3xl p-lg border border-outline-variant shadow-2xl space-y-md relative neomorphic-raised">
            <button 
              onClick={() => setShowAllStrengths(false)}
              className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center bg-surface border border-outline-variant text-on-surface-variant hover:text-primary neomorphic-raised active:neomorphic-inset transition-all"
            >
              <span className="material-symbols-outlined">close</span>
            </button>

            <h3 className="font-h3 text-green-700 font-bold flex items-center gap-xs">
              <span className="material-symbols-outlined">thumb_up</span>
              Key Strengths (Full List)
            </h3>

            <div className="space-y-xs max-h-[50vh] overflow-y-auto pr-xs">
              {evaluationResult.strengths && evaluationResult.strengths.map((str, index) => (
                <div key={index} className="text-xs p-sm bg-green-50/50 rounded-xl text-green-900 border border-green-100 font-medium">
                  {str}
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-xs">
              <Button onClick={() => setShowAllStrengths(false)}>Close</Button>
            </div>
          </div>
        </div>
      )}

      {/* Gaps View All Modal */}
      {showAllGaps && evaluationResult && (
        <div className="fixed inset-0 bg-surface/80 backdrop-blur-sm z-50 flex items-center justify-center p-md animate-fade-in">
          <div className="bg-surface max-w-[500px] w-full rounded-3xl p-lg border border-outline-variant shadow-2xl space-y-md relative neomorphic-raised">
            <button 
              onClick={() => setShowAllGaps(false)}
              className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center bg-surface border border-outline-variant text-on-surface-variant hover:text-primary neomorphic-raised active:neomorphic-inset transition-all"
            >
              <span className="material-symbols-outlined">close</span>
            </button>

            <h3 className="font-h3 text-primary-container font-bold flex items-center gap-xs">
              <span className="material-symbols-outlined">warning</span>
              Skill Gaps & Suggestions (Full List)
            </h3>

            <div className="space-y-xs max-h-[50vh] overflow-y-auto pr-xs">
              {evaluationResult.gaps && evaluationResult.gaps.map((gap, index) => (
                <div key={index} className="text-xs p-sm bg-orange-50/50 rounded-xl text-primary-container border border-orange-100 font-medium">
                  {gap}
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-xs">
              <Button onClick={() => setShowAllGaps(false)}>Close</Button>
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
