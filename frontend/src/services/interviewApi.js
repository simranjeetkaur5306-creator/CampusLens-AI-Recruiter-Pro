import api from "./api";

// Paths from your real route list.
export const INTERVIEW_ENDPOINTS = {
  forJob: (jobId) => `/api/interviews/jobs/${jobId}/questions/`,
  history: "/api/interviews/questions/",
};

export const CATEGORIES = [
  ["technical", "Technical"],
  ["conceptual", "Conceptual"],
  ["project_based", "Project-based"],
  ["hr", "HR"],
];

const KEYS = {
  technical: "technical",
  conceptual: "conceptual",
  project_based: "project_based",
  project: "project_based",
  "project-based": "project_based",
  hr: "hr",
};

const asQuestion = (q) =>
  typeof q === "string"
    ? { question: q, tests: "" }
    : { question: q?.question ?? q?.text ?? "", tests: q?.tests ?? q?.assesses ?? "" };

const keyOf = (v) => KEYS[String(v ?? "").toLowerCase().replace(/\s+/g, "_")];

// Accepts { technical: [...], ... } or a flat list with a category/type field.
export function normalizeSet(d) {
  const raw = d?.questions ?? d ?? {};
  const out = { technical: [], conceptual: [], project_based: [], hr: [] };

  if (Array.isArray(raw)) {
    raw.forEach((q) => {
      const key = keyOf(q?.category ?? q?.type ?? q?.question_type);
      if (key) out[key].push(asQuestion(q));
    });
  } else if (typeof raw === "object") {
    Object.entries(raw).forEach(([k, v]) => {
      const key = keyOf(k);
      if (key && Array.isArray(v)) out[key] = v.map(asQuestion).filter((q) => q.question);
    });
  }

  return {
    id: d?.id,
    jobId: d?.job && typeof d.job === "object" ? d.job.id : d?.job ?? d?.job_id ?? null,
    createdAt: d?.created_at ?? null,
    source: d?.source ?? "",
    model: d?.model_name ?? d?.model ?? "",
    notice: d?.notice ?? d?.message ?? "",
    questions: out,
  };
}

// Tries POST (generate). Falls back to GET if the route only supports reading.
export async function generateQuestions(jobId, count) {
  const url = INTERVIEW_ENDPOINTS.forJob(jobId);
  let res;
  try {
    res = await api.post(url, { count }, { timeout: 90000 });
  } catch (err) {
    if (err.response?.status !== 405) throw err;
    res = await api.get(url, { timeout: 90000 });
  }
  return normalizeSet(res.data);
}

export async function getQuestionHistory(jobId) {
  const { data } = await api.get(INTERVIEW_ENDPOINTS.history);
  const list = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];
  return list
    .map(normalizeSet)
    .filter((s) => s.jobId == null || String(s.jobId) === String(jobId));
}