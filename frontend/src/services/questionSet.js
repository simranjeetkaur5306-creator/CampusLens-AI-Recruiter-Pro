// Real response of the interviews API:
// { id, audience, job:{id,job_title,company_name}, application, used_resume, candidate_name,
//   question_count, categories:{technical:"Technical",...}, questions:{technical:[{question,skill,difficulty,answer_guide}],...},
//   model_name, prompt_version, created_at, note }
const DEFAULT_LABELS = { technical: "Technical", conceptual: "Conceptual", project_based: "Project-based", hr: "HR" };

const str = (v) => (typeof v === "string" ? v.trim() : "");

export function normalizeQuestionSet(d) {
  const labels = d?.categories && typeof d.categories === "object" ? d.categories : DEFAULT_LABELS;
  const raw = d?.questions && typeof d.questions === "object" ? d.questions : {};
  const sections = Object.keys(labels).map((key) => ({
    key,
    label: str(labels[key]) || key,
    items: (Array.isArray(raw[key]) ? raw[key] : [])
      .map((q) => ({
        question: str(q?.question),
        skill: str(q?.skill),
        difficulty: str(q?.difficulty).toLowerCase(),
        answerGuide: str(q?.answer_guide),
      }))
      .filter((q) => q.question),
  }));
  return {
    id: d?.id ?? null,
    jobId: d?.job?.id ?? null,
    jobTitle: d?.job?.job_title ?? "",
    candidateName: d?.candidate_name ?? "",
    usedResume: Boolean(d?.used_resume),
    count: d?.question_count ?? sections.reduce((n, s) => n + s.items.length, 0),
    model: d?.model_name ?? "",
    note: d?.note ?? "",
    createdAt: d?.created_at ?? null,
    sections,
  };
}