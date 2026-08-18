import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://docmind-ai-assistant-backend.onrender.com/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Inject JWT Access Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('docmind_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 Unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and trigger logout broadcast event if unauthorized
      const token = localStorage.getItem('docmind_access_token');
      if (token) {
        localStorage.removeItem('docmind_access_token');
        localStorage.removeItem('docmind_refresh_token');
        localStorage.removeItem('docmind_user');
        window.dispatchEvent(new Event('docmind_unauthorized'));
      }
    }
    return Promise.reject(error);
  }
);

// Auth Endpoints
export const googleLogin = async (googleIdToken) => {
  const response = await apiClient.post('/auth/google/', { token: googleIdToken });
  return response.data;
};

export const fetchCurrentUser = async () => {
  const response = await apiClient.get('/auth/me/');
  return response.data;
};

// Document Endpoints
export const fetchDocuments = async () => {
  const response = await apiClient.get('/documents/');
  return response.data;
};

export const fetchDocumentDetails = async (id) => {
  const response = await apiClient.get(`/documents/${id}/`);
  return response.data;
};

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post('/documents/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const deleteDocument = async (id) => {
  const response = await apiClient.delete(`/documents/${id}/`);
  return response.data;
};

export const reanalyzeDocument = async (id, focus = null) => {
  const payload = focus ? { focus } : {};
  const response = await apiClient.post(`/documents/${id}/reanalyze/`, payload);
  return response.data;
};

// Chat Endpoints
export const fetchChatSessions = async () => {
  const response = await apiClient.get('/chat/sessions/');
  return response.data;
};

export const createChatSession = async (documentId, title = '') => {
  const payload = { document: documentId };
  if (title) payload.title = title;
  const response = await apiClient.post('/chat/sessions/', payload);
  return response.data;
};

export const deleteChatSession = async (sessionId) => {
  const response = await apiClient.delete(`/chat/sessions/${sessionId}/`);
  return response.data;
};

export const fetchSessionMessages = async (sessionId) => {
  const response = await apiClient.get(`/chat/sessions/${sessionId}/messages/`);
  return response.data;
};

export const sendChatMessage = async (sessionId, content) => {
  const response = await apiClient.post(`/chat/sessions/${sessionId}/send-message/`, { content });
  return response.data;
};

// AI Provider Config Endpoints
export const fetchAIConfig = async () => {
  const response = await apiClient.get('/ai/config/');
  return response.data;
};

export const updateAIConfig = async (apiKey) => {
  const response = await apiClient.post('/ai/config/', { api_key: apiKey });
  return response.data;
};

export default apiClient;
