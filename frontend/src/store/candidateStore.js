import { create } from 'zustand';

export const useCandidateStore = create((set) => ({
  parsedProfile: null,
  candidateId: null,
  evaluationResult: null,
  projectResults: [],
  rewriteResults: null,

  setParsedProfile: (profile, id = null) => {
    set({ 
      parsedProfile: profile, 
      candidateId: (id === 0 ? null : id) 
    });
  },

  setCandidateId: (id) => {
    set({ candidateId: id });
  },

  setEvaluationResult: (result) => set({ evaluationResult: result }),
  setProjectResults: (projects) => set({ projectResults: projects }),
  setRewriteResults: (results) => set({ rewriteResults: results }),

  clearSession: () => {
    set({ 
      parsedProfile: null, 
      candidateId: null, 
      evaluationResult: null, 
      projectResults: [],
      rewriteResults: null
    });
  }
}));
