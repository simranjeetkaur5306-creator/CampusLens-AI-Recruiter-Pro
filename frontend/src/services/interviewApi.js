import api, { fetchAll } from "./api";
import { normalizeQuestionSet } from "./questionSet";

// Real backend paths (interviews app).
export const INTERVIEW_ENDPOINTS = {
  forJob: (jobId) => `/api/interviews/jobs/${jobId}/questions/`,
  history: "/api/interviews/questions/",
  detail: (id) => `/api/interviews/questions/${id}/`,
};

// POST: generates and saves a new practice set (needs an active resume). Counts are fixed by the backend.
export async function generateQuestions(jobId) {
  const { data } = await api.post(INTERVIEW_ENDPOINTS.forJob(jobId), {}, { timeout: 90000 });
  return normalizeQuestionSet(data);
}

export async function getQuestionHistory(jobId) {
  const rows = await fetchAll(INTERVIEW_ENDPOINTS.history, { job: jobId });
  return rows.map(normalizeQuestionSet);
}

export async function deleteQuestionSet(id) {
  await api.delete(INTERVIEW_ENDPOINTS.detail(id));
}