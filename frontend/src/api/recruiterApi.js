import api from './authApi';

export const recruiterApi = {
  getMetrics: async () => {
    const response = await api.get('/metrics');
    return response.data;
  },

  uploadResume: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/v1/resume/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  },

  getResumeStatus: async (resumeId) => {
    const response = await api.get(`/v1/resume/status/${resumeId}`);
    return response.data;
  },

  getCandidate: async (candidateId) => {
    const response = await api.get(`/candidate/${candidateId}`);
    return response.data;
  },

  normalizeJD: async (jdText) => {
    const response = await api.post('/jd/rewrite', { jd_text: jdText });
    return response.data;
  },

  evaluateJD: async (payload) => {
    const response = await api.post('/evaluate-jd', payload);
    return response.data;
  }
};
