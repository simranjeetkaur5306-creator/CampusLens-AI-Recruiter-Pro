import api from "./api";

// Paths taken from your real `dump_urls.py` output. Edit ONLY this block if routes change.
export const CANDIDATE_ENDPOINTS = {
  profile: "/api/candidates/me/",
  resumes: "/api/resumes/",
  resumeUpload: "/api/resumes/upload/",
  recommendations: "/api/matching/recommendations/",
  applications: "/api/applications/",
  myApplications: "/api/applications/me/",
  jobs: "/api/jobs/",
  skillGap: (jobId) => `/api/skill-gap/jobs/${jobId}/`,
  aiSummary: (jobId) => `/api/skill-gap/jobs/${jobId}/ai-summary/`,
};

/* ---------- normalizers: accept several possible backend shapes ---------- */

const unwrapList = (data) =>
  Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : [];

const labelOf = (x) => {
  if (x == null) return "";
  if (typeof x === "string") return x.trim();
  if (typeof x === "number") return String(x);
  if (typeof x === "object") {
    return Object.values(x)
      .filter((v) => typeof v === "string" && v.trim())
      .join(" · ");
  }
  return "";
};

const skillOf = (x) =>
  x && typeof x === "object" ? x.name ?? x.skill ?? labelOf(x) : labelOf(x);

const asArray = (v) => (Array.isArray(v) ? v : v ? [v] : []);

export const toLabels = (v) => asArray(v).map(labelOf).filter(Boolean);

export const toSkills = (v) =>
  (typeof v === "string" ? v.split(",") : asArray(v)).map(skillOf).filter(Boolean);

// Backend may return 0-1 (cosine) or 0-100. Values <= 1 are treated as fractions.
export function normalizeScore(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  return Math.max(0, Math.min(100, Math.round(n <= 1 ? n * 100 : n)));
}

export function normalizeResume(r) {
  const file = r.file ? decodeURIComponent(String(r.file).split("/").pop()) : "";
  return {
    id: r.id,
    fileName: r.original_filename ?? r.file_name ?? (file || "Resume"),
    uploadedAt: r.uploaded_at ?? r.created_at ?? null,
    name: r.name ?? r.full_name ?? "",
    email: r.email ?? "",
    phone: r.phone ?? "",
    skills: toSkills(r.skills ?? r.extracted_skills),
    education: toLabels(r.education),
    experience: toLabels(r.experience),
    projects: toLabels(r.projects),
    certifications: toLabels(r.certifications),
  };
}

export function normalizeJob(item) {
  const job = item.job ?? item.job_description ?? item;
  return {
    id: job.id,
    title: job.title ?? "Untitled role",
    company: job.company_name ?? job.recruiter?.company_name ?? job.company ?? "",
    location: job.location ?? "",
    description: job.description ?? "",
    experienceLevel: job.experience_level ?? "",
    requiredSkills: toSkills(job.required_skills ?? job.skills),
    matchScore: normalizeScore(
      item.match_score ?? item.match_percentage ?? item.score ?? item.similarity_score ??
        item.similarity ?? item.cosine_similarity ?? job.match_score
    ),
    matchedSkills: toSkills(item.matched_skills),
    missingSkills: toSkills(item.missing_skills),
  };
}

function normalizeInterview(i) {
  if (!i || typeof i !== "object") return null;
  return {
    date: i.interview_date ?? i.date ?? null,
    time: i.interview_time ?? i.time ?? "",
    mode: i.interview_mode ?? i.mode ?? "",
    location: i.meeting_link ?? i.location ?? "",
    details: i.details ?? "",
  };
}

export function normalizeApplication(a) {
  const job = typeof a.job === "object" && a.job ? a.job : a.job_description ?? {};
  return {
    id: a.id,
    jobId: job.id ?? (typeof a.job !== "object" ? a.job : undefined) ?? a.job_id,
    jobTitle: job.title ?? a.job_title ?? "Job",
    company: job.company_name ?? a.company_name ?? "",
    status: String(a.status ?? "applied").toLowerCase(),
    appliedAt: a.applied_at ?? a.created_at ?? null,
    matchScore: normalizeScore(a.match_score ?? a.score),
    interview: normalizeInterview(a.interview ?? (Array.isArray(a.interviews) ? a.interviews[0] : null)),
  };
}

export function normalizeGap(d) {
  return {
    matched: toSkills(d.matched_skills ?? d.available_skills ?? d.matched ?? d.available),
    partial: toSkills(d.partial_skills ?? d.partially_matched_skills ?? d.partial),
    missing: toSkills(d.missing_skills ?? d.missing),
    recommendations: toLabels(d.recommendations ?? d.learning_recommendations ?? d.suggestions),
    summary: typeof d.summary === "string" ? d.summary : d.ai_summary ?? "",
  };
}

/* ---------- API calls ---------- */

export async function getProfile() {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.profile);
  if (Array.isArray(data)) return data[0] ?? {};
  if (Array.isArray(data?.results)) return data.results[0] ?? {};
  return data ?? {};
}

export async function updateProfile(changes) {
  const { data } = await api.patch(CANDIDATE_ENDPOINTS.profile, changes);
  return data;
}

export async function getResumes() {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.resumes);
  return unwrapList(data)
    .map(normalizeResume)
    .sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0));
}

export async function uploadResume(file, onProgress) {
  const form = new FormData();
  form.append("file", file); // field name assumed: "file"
  const { data } = await api.post(CANDIDATE_ENDPOINTS.resumeUpload, form, {
    timeout: 120000,
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return normalizeResume(data?.resume ?? data);
}

export async function getRecommendations() {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.recommendations);
  return unwrapList(data).map(normalizeJob);
}

export async function getApplications() {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.myApplications);
  return unwrapList(data).map(normalizeApplication);
}

export async function getJob(id) {
  const { data } = await api.get(`${CANDIDATE_ENDPOINTS.jobs}${id}/`);
  return normalizeJob(data);
}

// Sends { job: id }. If the serializer asks for "job_id" instead, it retries once with that.
export async function applyToJob(jobId) {
  try {
    const { data } = await api.post(CANDIDATE_ENDPOINTS.applications, { job: jobId });
    return data;
  } catch (err) {
    const d = err.response?.data;
    if (err.response?.status === 400 && d && typeof d === "object" && "job_id" in d) {
      const { data } = await api.post(CANDIDATE_ENDPOINTS.applications, { job_id: jobId });
      return data;
    }
    throw err;
  }
}

export async function getSkillGap(jobId) {
  const { data } = await api.get(CANDIDATE_ENDPOINTS.skillGap(jobId));
  return normalizeGap(data?.skill_gap ?? data?.analysis ?? data);
}

// LLM-written summary. Tries POST first, falls back to GET if the route is GET-only.
export async function getAiSummary(jobId) {
  const url = CANDIDATE_ENDPOINTS.aiSummary(jobId);
  let res;
  try {
    res = await api.post(url, {}, { timeout: 90000 });
  } catch (err) {
    if (err.response?.status !== 405) throw err;
    res = await api.get(url, { timeout: 90000 });
  }
  const d = res.data;
  const s = typeof d === "string" ? d : d?.summary ?? d?.ai_summary ?? d?.text;
  return typeof s === "string" ? s : s?.summary ?? "";
}

// Jobs the candidate can pick in selectors: recommended + already applied (deduplicated).
export async function getJobOptions() {
  const [recs, apps] = await Promise.allSettled([getRecommendations(), getApplications()]);
  if (recs.status === "rejected" && apps.status === "rejected") throw recs.reason;
  const map = new Map();
  if (recs.status === "fulfilled") {
    recs.value.forEach((j) => map.set(String(j.id), { id: j.id, title: j.title, company: j.company }));
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