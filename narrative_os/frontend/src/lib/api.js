import axios from 'axios';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '');

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export async function getCurrentWorkflow() {
  const response = await api.get('/workflow/current');
  return response.data;
}

export async function getWorkflow(chapterNo) {
  const response = await api.get(`/workflow/${chapterNo}`);
  return response.data;
}

export async function saveWorkflowDraft(chapterNo, payload) {
  const response = await api.post(`/workflow/${chapterNo}/save-draft`, payload);
  return response.data;
}

export async function saveWorkflowLedger(chapterNo, payload) {
  const response = await api.post(`/workflow/${chapterNo}/save-ledger`, payload);
  return response.data;
}

export async function generateWorkflowRadar(chapterNo) {
  const response = await api.post(`/workflow/${chapterNo}/generate-radar`);
  return response.data;
}

export async function finalizeWorkflow(chapterNo) {
  const response = await api.post(`/workflow/${chapterNo}/finalize`);
  return response.data;
}

export async function getWorkflowCharacterContext(chapterNo, payload) {
  const response = await api.post(`/workflow/${chapterNo}/character-context`, payload);
  return response.data;
}
