import api, { fetchAll } from "./api";

// Real backend paths. Edit ONLY this block if a route changes.
export const CANDIDATE_ENDPOINTS = {
  profile: "/api/candidates/me/",
  resumes: "/api/resumes/",
  resume: (id) => `/api/resumes/${id}/`,
  resumeUpload: "/api/resumes/upload/",
  activateResume: (id) => `/api/resumes/${id}/activate/`,
  recommendations: "/api/matching/recommendations/",
  applications: "/api/applications/",
  myApplications: "/api/applications/me/",
  job: (id) => `/api/jobs/${id}/`,
  skillGap: (jobId) => `/api/skill-gap/jobs/${jobId}/`,
  aiSummary: (jobId) => `/api/skill-gap/jobs/${jobId}/ai-summary/`,
};

/* ---------- small helpers ---------- */

const names = (list) =>
  (Array.isArray(list) ? list : []).map((s) => (typeof s === "string" ? s : s?.name ?? s?.skill)).filter(Boolean);

const arr = (v) => (Array.isArray(v) ? v : []);

const percent = (v) => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : Math.max(0, Math.min(100, Math.round(n)));
};

/* ---------- normalizers (shapes taken from the backend serializers) ---------- */

// Works for both the resume list (no parsed sections) and the resume detail.
export function normalizeResume(r) {
  const c = r.contact && typeof r.contact === "object" ? r.contact : {};
  return {
    id: r.id,
    fileName: r.original_filename ?? "Resume",
    fileType: r.file_type ?? "",
    fileSize: r.file_size ?? null,
    uploadedAt: r.uploaded_at ?? null,
    isActive: Boolean(r.is_active),
    parsingStatus: r.parsing_status ?? "",
    parsingError: r.parsing_error ?? "",
    contact: {
      name: c.name ?? "",
      email: c.email ?? "",
      phone: c.phone ?? "",
      linkedin: c.linkedin ?? "",
      github: c.github ?? "",
    },
    skills: names(r.skills),
    education: arr(r.education),
    experience: arr(r.experience),
    projects: arr(r.projects),
    certifications: arr(r.certifications),
  };
}

export function normalizeJob(j) {
  return {
    id: j.id,
    title: j.job_title ?? "Untitled role",
    company: j.company_name ?? "",
    location: j.location ?? "",
    jobType: j.job_type ?? "",
    description: j.description ?? "",
    requiredSkills: names(j.required_skills),
    requiredExperience: j.required_experience ?? 0,
    requiredEducation: j.required_education ?? "",
    salaryRange: j.salary_range ?? "",
    isActive: j.is_active !== false,
  };
}

// One row of GET /api/matching/recommendations/
export function normalizeRecommendation(row) {
  return {
    ...normalizeJob(row.job ?? {}),
    matchPercent: percent(row.match_percent),
    matched: names(row.matching_skills),
    missing: names(row.missing_skills),
    alreadyApplied: Boolean(row.already_applied),
  };
}

export function normalizeApplication(a) {
  const job = a.job ?? {};
  const resume = a.resume ?? null;
  return {
    id: a.id,
    status: String(a.status ?? "applied").toLowerCase(),
    appliedAt: a.applied_at ?? null,
    jobId: job.id ?? null,
    jobTitle: job.job_title ?? "Job",
    company: job.company_name ?? "",
    location: job.location ?? "",
    jobType: job.job_type ?? "",
    jobOpen: job.is_active !== false,
    resumeName: resume?.original_filename ?? "",
  };
}

const gapRows = (list) =>
  arr(list).map((r) => ({
    skill: r.skill ?? "",
    category: r.category ?? "",
    note: r.evidence?.note ?? "",
    basedOn: names(r.evidence?.skills),
  }));

export function normalizeGap(d) {
  return {
    jobId: d.job?.id ?? null,
    jobTitle: d.job?.job_title ?? "",
    resumeName: d.resume?.original_filename ?? "",
    resumeActive: Boolean(d.resume?.is_active),
    summary: d.summary ?? "",
    total: d.total_required ?? 0,
    coverage: percent(d.coverage_percent),
    coverageRule: d.coverage_rule ?? "",
    matched: gapRows(d.matched),
    partial: gapRows(d.partial),
    missing: gapRows(d.missing),
    plan: arr(d.learning_plan).map((p) => ({
      priority: p.priority ?? 0,
      skill: p.skill ?? "",
      status: p.status ?? "",
      learnAfter: names(p.learn_after),
      topics: arr(p.topics).filter((t) => typeof t === "string"),
      projectIdea: p.project_idea ?? "",
      source: p.source ?? "",
    })),
    disclaimer: d.disclaimer ?? "",
  };
}

/* ---------- profile ---------- */

export async function getProfile() {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.profile);
  return data ?? {};
}

export async function updateProfile(changes) {
  const { data } = await api.patch(CANDIDATE_ENDPOINTS.profile, changes);
  return data;
}

/* ---------- resumes ---------- */

export async function getResumes() {
  const rows = await fetchAll(CANDIDATE_ENDPOINTS.resumes);
  return rows.map(normalizeResume);
}

export async function getResumeDetail(id) {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.resume(id));
  return normalizeResume(data);
}

// Resolves to { message, resume }. A file with unreadable text is still saved, with parsingStatus "failed".
export async function uploadResume(file, onProgress) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post(CANDIDATE_ENDPOINTS.resumeUpload, form, {
    timeout: 120000,
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return { message: data?.message ?? "", resume: normalizeResume(data?.resume ?? {}) };
}

export async function activateResume(id) {
  await api.post(CANDIDATE_ENDPOINTS.activateResume(id), {});
}

export async function deleteResume(id) {
  await api.delete(CANDIDATE_ENDPOINTS.resume(id));
}

/* ---------- jobs, recommendations, applications ---------- */

// includeApplied=false (default) hides jobs you already applied to. The API returns at most 50.
export async function getRecommendations({ includeApplied = false, limit = 50, minPercent } = {}) {
  const params = { limit, include_applied: includeApplied };
  if (minPercent) params.min_percent = minPercent;
  const { data } = await api.get(CANDIDATE_ENDPOINTS.recommendations, { params });
  return {
    resumeName: data?.resume?.original_filename ?? "",
    items: arr(data?.results).map(normalizeRecommendation),
  };
}

export async function getJob(id) {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.job(id));
  return normalizeJob(data);
}

export async function getApplications() {
  const rows = await fetchAll(CANDIDATE_ENDPOINTS.myApplications);
  return rows.map(normalizeApplication);
}

export async function applyToJob(jobId) {
  const { data } = await api.post(CANDIDATE_ENDPOINTS.applications, { job: jobId });
  return normalizeApplication(data?.application ?? {});
}

// Jobs the candidate can pick in selectors: matched jobs + jobs already applied to (deduplicated).
export async function getJobOptions() {
  const [recs, apps] = await Promise.allSettled([getRecommendations({ includeApplied: true }), getApplications()]);
  if (recs.status === "rejected" && apps.status === "rejected") throw recs.reason;
  const map = new Map();
  if (recs.status === "fulfilled") {
    recs.value.items.forEach((j) => map.set(String(j.id), { id: j.id, title: j.title, company: j.company }));
  }
  if (apps.status === "fulfilled") {
    apps.value.forEach((a) => {
      if (a.jobId != null && !map.has(String(a.jobId))) {
        map.set(String(a.jobId), { id: a.jobId, title: a.jobTitle, company: a.company });
      }
    });
  }
  return [...map.values()];
}

/* ---------- skill gap ---------- */

// Rule-based comparison (no AI). Always grounded in the skills found on the resume.
export async function getSkillGap(jobId) {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.skillGap(jobId));
  return normalizeGap(data ?? {});
}

// POST, rate limited, calls the LLM. The lists still come from the rule-based analysis.
export async function getAiSummary(jobId) {
  const { data } = await api.post(CANDIDATE_ENDPOINTS.aiSummary(jobId), {}, { timeout: 90000 });
  return { text: data?.ai_summary ?? "", model: data?.model_name ?? "", note: data?.note ?? "" };
}