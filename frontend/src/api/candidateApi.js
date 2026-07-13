import api from './authApi';

export const candidateApi = {
  uploadResume: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/candidate/upload-resume', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  },

  selfEvaluate: async (payload) => {
    const response = await api.post('/candidate/agent-self-evaluation', payload);
    return response.data;
  },

  getProjects: async (payload) => {
    const response = await api.post('/candidate/projects', payload);
    return response.data;
  },

  rewriteResume: async (payload) => {
    const response = await api.post('/candidate/resume-rewrite', payload);
    return response.data;
  },

  persist: async (candidateData) => {
    const response = await api.post('/candidate/persist', candidateData);
    return response.data;
  },

  startInterview: async (payload) => {
    const response = await api.post('/candidate/interview/start', payload);
    return response.data;
  },

  submitInterviewAnswer: async (payload) => {
    const response = await api.post('/candidate/interview/submit', payload);
    return response.data;
  }
};
