export default function About() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-bold tracking-tight">About CampusLens AI</h1>
      <p className="mt-4 text-slate-600">
        Traditional applicant tracking systems mostly rely on keyword matching, which can miss qualified
        candidates whose wording differs from the job description. CampusLens AI compares resumes and job
        descriptions by semantic meaning and adds ranking, skill-gap analysis and interview assistance.
      </p>

      <h2 className="mt-10 text-xl font-semibold">Objectives</h2>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-slate-600">
        <li>Role-based platform for candidates and recruiters with JWT authentication</li>
        <li>Resume parsing and structured information extraction</li>
        <li>Embedding-based matching with pgvector and cosine similarity</li>
        <li>Candidate ranking, skill-gap analysis and AI interview questions</li>
        <li>Dashboards with recruitment analytics</li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold">Limitations</h2>
      <p className="mt-3 text-slate-600">
        The system is decision support, not an automatic hiring tool. Pretrained models can carry bias,
        scanned resumes may parse poorly, and LLM features depend on a third-party API.
      </p>

      <p className="mt-10 text-sm text-slate-500">
        Developed by Simranjeet Kaur and Khushi Sharma · Guide: Er. Sourabh Budhiraja · ACEAR, Kurukshetra University.
      </p>
    </div>
  );
}
