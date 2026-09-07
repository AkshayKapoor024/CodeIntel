// API Client - all calls to FastAPI backend
const BASE_URL = 'http://localhost:8080';

async function request(method, path, body = null) {
  const opts = {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// Auth
export const authApi = {
  register: (payload) => request('POST', '/api/auth/register', payload),
  login: (payload) => request('POST', '/api/auth/login', payload),
  logout: () => request('POST', '/api/auth/logout'),
  me: () => request('GET', '/api/auth/me'),
};

// Repositories
export const repoApi = {
  list: () => request('GET', '/api/repositories'),
  create: (payload) => request('POST', '/api/repositories', payload),
  get: (id) => request('GET', `/api/repositories/${id}`),
  delete: (id) => request('DELETE', `/api/repositories/${id}`),
  analyze: (id) => request('POST', `/api/repositories/${id}/analyze`),
  status: (id) => request('GET', `/api/repositories/${id}/status`),
  analysis: (id) => request('GET', `/api/repositories/${id}/analysis`),
  report: (id) => request('GET', `/api/repositories/${id}/report`),
  structure: (id) => request('GET', `/api/repositories/${id}/structure`),
  issues: (id) => request('GET', `/api/repositories/${id}/issues`),
  getFile: (id, filePath) => request('GET', `/api/repositories/${id}/files/${encodeURIComponent(filePath)}`),
};

// Conversations
export const chatApi = {
  listConversations: (repoId) => request('GET', `/api/repositories/${repoId}/conversations`),
  createConversation: (repoId) => request('POST', `/api/repositories/${repoId}/conversations`),
  getConversation: (convId) => request('GET', `/api/conversations/${convId}`),
  deleteConversation: (convId) => request('DELETE', `/api/conversations/${convId}`),
  sendMessage: (convId, message) => request('POST', `/api/conversations/${convId}/messages`, { message }),
};
