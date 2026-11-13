// ONLY file that knows backend auth URLs. Match these with your Phase 3 urls.py.
export const ENDPOINTS = {
  login: "/api/auth/login/",
  refresh: "/api/auth/token/refresh/",
  me: "/api/auth/me/",
  registerCandidate: "/api/auth/register/candidate/",
  registerRecruiter: "/api/auth/register/recruiter/",
};
