import { Link, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import CandidateLayout from "./layouts/CandidateLayout";
import PublicLayout from "./layouts/PublicLayout";
import RecruiterLayout from "./layouts/RecruiterLayout";
import About from "./pages/public/About";
import Landing from "./pages/public/Landing";
import Login from "./pages/public/Login";
import RegisterCandidate from "./pages/public/RegisterCandidate";
import RegisterRecruiter from "./pages/public/RegisterRecruiter";
import Applications from "./pages/candidate/Applications";
import CandidateDashboard from "./pages/candidate/CandidateDashboard";
import InterviewPrep from "./pages/candidate/InterviewPrep";
import JobDetails from "./pages/candidate/JobDetails";
import Profile from "./pages/candidate/Profile";
import Recommendations from "./pages/candidate/Recommendations";
import ResumeAnalysis from "./pages/candidate/ResumeAnalysis";
import ResumeUpload from "./pages/candidate/ResumeUpload";
import SkillGap from "./pages/candidate/SkillGap";
import ApplicantDetails from "./pages/recruiter/ApplicantDetails";
import Applicants from "./pages/recruiter/Applicants";
import CompanyProfile from "./pages/recruiter/CompanyProfile";
import JobEditor from "./pages/recruiter/JobEditor";
import ManageJobs from "./pages/recruiter/ManageJobs";
import Ranking from "./pages/recruiter/Ranking";
import RecruiterDashboard from "./pages/recruiter/RecruiterDashboard";

function NotFound() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3">
      <h1 className="text-3xl font-bold">404</h1>
      <p className="text-slate-500">Page not found.</p>
      <Link to="/" className="text-brand-600 hover:underline">Back to home</Link>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/about" element={<About />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register/candidate" element={<RegisterCandidate />} />
        <Route path="/register/recruiter" element={<RegisterRecruiter />} />
      </Route>

      <Route
        path="/candidate"
        element={<ProtectedRoute role="candidate"><CandidateLayout /></ProtectedRoute>}
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<CandidateDashboard />} />
        <Route path="profile" element={<Profile />} />
        <Route path="resume-upload" element={<ResumeUpload />} />
        <Route path="resume-analysis" element={<ResumeAnalysis />} />
        <Route path="recommendations" element={<Recommendations />} />
        <Route path="jobs/:id" element={<JobDetails />} />
        <Route path="applications" element={<Applications />} />
        <Route path="skill-gap" element={<SkillGap />} />
        <Route path="interview-prep" element={<InterviewPrep />} />
      </Route>

      <Route
        path="/recruiter"
        element={<ProtectedRoute role="recruiter"><RecruiterLayout /></ProtectedRoute>}
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<RecruiterDashboard />} />
        <Route path="company" element={<CompanyProfile />} />
        <Route path="jobs" element={<ManageJobs />} />
        <Route path="jobs/new" element={<JobEditor />} />
        <Route path="jobs/:id/edit" element={<JobEditor />} />
        <Route path="applicants" element={<Applicants />} />
        <Route path="applicants/:id" element={<ApplicantDetails />} />
        <Route path="ranking" element={<Ranking />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}