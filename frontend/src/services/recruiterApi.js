import api, { fetchAll } from "./api";
import { normalizeQuestionSet } from "./questionSet";

// Real backend paths. Edit ONLY this block if a route changes.
export const RECRUITER_ENDPOINTS = {
  profile: "/api/recruiters/me/",
  jobs: "/api/jobs/manage/",
  job: (id) => `/api/jobs/manage/${id}/`,
  received: "/api/applications/received/",
  application: (id) => `/api/applications/${id}/`,
  status: (id) => `/api/applications/${id}/status/`,
  resumeFile: (id) => `/api/applications/${id}/resume-file/`,
  ranking: (jobId) => `/api/matching/jobs/${jobId}/ranking/`,
  questions: (applicationId) => `/api/interviews/applications/${applicationId}/questions/`,
};

export const JOB_TYPES = [
  ["full_time", "Full-time"],
  ["part_time", "Part-time"],
  ["internship", "Internship"],
  ["contract", "Contract"],
  ["freelance", "Freelance"],
];

const percent = (v) => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : Math.max(0, Math.min(100, Math.round(n)));
};

const names = (list) =>
  (Array.isArray(list) ? list : []).map((s) => (typeof s === "string" ? s : s?.name)).filter(Boolean);

/* ---------- jobs ---------- */

export function normalizeManagedJob(j) {
  return {
    id: j.id,
    title: j.job_title ?? "Untitled role",
    company: j.company_name ?? "",
    location: j.location ?? "",
    jobType: j.job_type ?? "full_time",
    description: j.description ?? "",
    requiredSkills: names(j.required_skills),
    requiredExperience: j.required_experience ?? 0,
    requiredEducation: j.required_education ?? "",
    salaryRange: j.salary_range ?? "",
    isActive: Boolean(j.is_active),
    createdAt: j.created_at ?? null,
  };
}

// "Python, sql ,python" -> ["Python", "sql"]  (trimmed, duplicates removed ignoring case)
export function parseSkills(text) {
  const seen = new Set();
  const out = [];
  for (const raw of String(text || "").split(/[,\n]/)) {
    const name = raw.trim().replace(/\s+/g, " ");
    if (name && !seen.has(name.toLowerCase())) {
      seen.add(name.toLowerCase());
      out.push(name);
    }
  }
  return out;
}

// The backend rejects unknown fields, so only real Job fields are sent.
// company_name is omitted when blank (the backend then uses the company in your profile).
export function toJobPayload(v) {
  const body = {
    job_title: v.title.trim(),
    location: v.location.trim(),
    job_type: v.jobType,
    description: v.description.trim(),
    required_skills: parseSkills(v.skills),
    required_experience: Number(v.requiredExperience) || 0,
    required_education: v.requiredEducation.trim(),
    salary_range: v.salaryRange.trim(),
    is_active: Boolean(v.isActive),
  };
  if (v.company.trim()) body.company_name = v.company.trim();
  return body;
}

export async function getManagedJobs() {
  const rows = await fetchAll(RECRUITER_ENDPOINTS.jobs);
  return rows.map(normalizeManagedJob);
}

export async function getManagedJob(id) {
  const { data } = await api.get(RECRUITER_ENDPOINTS.job(id));
  return normalizeManagedJob(data);
}

export async function createJob(values) {
  const { data } = await api.post(RECRUITER_ENDPOINTS.jobs, toJobPayload(values));
  return normalizeManagedJob(data);
}

export async function updateJob(id, values) {
  const { data } = await api.patch(RECRUITER_ENDPOINTS.job(id), toJobPayload(values));
  return normalizeManagedJob(data);
}

export async function setJobActive(id, isActive) {
  const { data } = await api.patch(RECRUITER_ENDPOINTS.job(id), { is_active: Boolean(isActive) });
  return normalizeManagedJob(data);
}

// A job that already has applications cannot be deleted (409); the error message says to unpublish it.
export async function deleteJob(id) {
  await api.delete(RECRUITER_ENDPOINTS.job(id));
}

/* ---------- company profile ---------- */

export async function getCompanyProfile() {
  const { data } = await api.get(RECRUITER_ENDPOINTS.profile);
  return data ?? {};
}

export async function updateCompanyProfile(changes) {
  const { data } = await api.patch(RECRUITER_ENDPOINTS.profile, changes);
  return data;
}

/* ---------- applicants ---------- */

export function normalizeApplicant(a) {
  const c = a.candidate ?? {};
  const job = a.job ?? {};
  const resume = a.resume ?? null;
  return {
    id: a.id,
    status: String(a.status ?? "applied").toLowerCase(),
    appliedAt: a.applied_at ?? null,
    updatedAt: a.updated_at ?? null,
    jobId: job.id ?? null,
    jobTitle: job.job_title ?? "Job",
    name: c.name || c.email || "Candidate",
    email: c.email ?? "",
    headline: c.headline ?? "",
    university: c.university ?? "",
    degree: c.degree ?? "",
    graduationYear: c.graduation_year ?? null,
    location: c.location ?? "",
    linkedinUrl: c.linkedin_url ?? "",
    githubUrl: c.github_url ?? "",
    resumeId: resume?.id ?? null,
    resumeName: resume?.original_filename ?? "",
    skills: names(resume?.skills),
  };
}

export function normalizeApplicantDetail(a) {
  const base = normalizeApplicant(a);
  const r = a.resume ?? null;
  return {
    ...base,
    resume: r && {
      id: r.id,
      fileName: r.original_filename ?? "Resume",
      fileType: r.file_type ?? "",
      uploadedAt: r.uploaded_at ?? null,
      hasFile: Boolean(r.has_file),
      contact: r.contact ?? {},
      skills: names(r.skills),
      education: Array.isArray(r.education) ? r.education : [],
      experience: Array.isArray(r.experience) ? r.experience : [],
      projects: Array.isArray(r.projects) ? r.projects : [],
      certifications: Array.isArray(r.certifications) ? r.certifications : [],
    },
  };
}

export async function getApplicants({ jobId, status } = {}) {
  const params = {};
  if (jobId) params.job = jobId;
  if (status) params.status = status;
  const rows = await fetchAll(RECRUITER_ENDPOINTS.received, params);
  return rows.map(normalizeApplicant);
}

export async function getApplicantDetail(id) {
  const { data } = await api.get(RECRUITER_ENDPOINTS.application(id));
  return normalizeApplicantDetail(data);
}

// status: "applied" | "shortlisted" | "rejected". The recruiter always decides; nothing is automatic.
export async function updateApplicationStatus(id, status) {
  const { data } = await api.patch(RECRUITER_ENDPOINTS.status(id), { status });
  return normalizeApplicant(data);
}

// Downloads the resume file through the authenticated API (it has no public URL).
export async function fetchResumeFile(applicationId) {
  try {
    const res = await api.get(RECRUITER_ENDPOINTS.resumeFile(applicationId), { responseType: "blob" });
    const type = res.headers?.["content-type"] || "application/octet-stream";
    return { blob: new Blob([res.data], { type }), type };
  } catch (err) {
    // With responseType "blob" an error body is also a Blob; read it so errorMessage() can show it.
    if (err.response?.data instanceof Blob) {
      try {
        err.response.data = JSON.parse(await err.response.data.text());
      } catch {
        err.response.data = null;
      }
    }
    throw err;
  }
}

export async function generateApplicantQuestions(applicationId) {
  const { data } = await api.post(RECRUITER_ENDPOINTS.questions(applicationId), {}, { timeout: 90000 });
  return normalizeQuestionSet(data);
}

/* ---------- ranking ---------- */

export function normalizeRankRow(r, index) {
  const c = r.candidate ?? {};
  const resume = r.resume ?? null;
  return {
    key: r.application_id ?? index,
    applicationId: r.application_id ?? null,
    rank: r.rank ?? null,
    scored: Boolean(r.scored),
    status: String(r.status ?? "applied").toLowerCase(),
    appliedAt: r.applied_at ?? null,
    name: c.name || c.email || "Candidate",
    email: c.email ?? "",
    headline: c.headline ?? "",
    university: c.university ?? "",
    resumeName: resume?.original_filename ?? "",
    skills: names(resume?.skills),
    score: percent(r.match_percent),
    matched: names(r.matching_skills),
    missing: names(r.missing_skills),
  };
}

export async function getRanking(jobId) {
  const { data } = await api.get(RECRUITER_ENDPOINTS.ranking(jobId));
  return {
    note: data?.note ?? "",
    total: data?.applicants_total ?? 0,
    scored: data?.applicants_scored ?? 0,
    rows: (Array.isArray(data?.results) ? data.results : []).map(normalizeRankRow),
  };
}