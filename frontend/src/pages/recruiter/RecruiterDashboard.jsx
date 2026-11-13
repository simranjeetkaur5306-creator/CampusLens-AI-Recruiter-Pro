import { useAuth } from "../../context/AuthContext";

// Temporary placeholder. The real dashboard is built in Phase 13/14.
export default function RecruiterDashboard() {
  const { user, logout } = useAuth();
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">Recruiter Dashboard (placeholder)</h1>
      <p className="mt-2 text-slate-600">Logged in as {user?.email} ({user?.role})</p>
      <button onClick={logout} className="mt-4 rounded-lg bg-slate-800 px-4 py-2 text-white">Logout</button>
    </div>
  );
}
