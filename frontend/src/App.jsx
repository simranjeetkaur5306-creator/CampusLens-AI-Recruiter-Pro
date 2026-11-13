import { Link, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import PublicLayout from "./layouts/PublicLayout";
import About from "./pages/public/About";
import Landing from "./pages/public/Landing";
import Login from "./pages/public/Login";
import RegisterCandidate from "./pages/public/RegisterCandidate";
import RegisterRecruiter from "./pages/public/RegisterRecruiter";
import CandidateDashboard from "./pages/candidate/CandidateDashboard";
import RecruiterDashboard from "./pages/recruiter/RecruiterDashboard";

function NotFound() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3">
      <h1 className="text-3xl font-bold">404</h1>
      <p className="text-slate-500">Page not found.</p>
      <Link to="/" className="text-indigo-600 hover:underline">Back to home</Link>
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
        path="/candidate/dashboard"
        element={<ProtectedRoute role="candidate"><CandidateDashboard /></ProtectedRoute>}
      />
      <Route
        path="/recruiter/dashboard"
        element={<ProtectedRoute role="recruiter"><RecruiterDashboard /></ProtectedRoute>}
      />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
