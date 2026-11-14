import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Building2, Briefcase, LayoutDashboard, ListOrdered, LogOut, Menu, PlusCircle, Users, X } from "lucide-react";
import { ToastProvider } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";

const NAV = [
  ["/recruiter/dashboard", "Dashboard", LayoutDashboard],
  ["/recruiter/company", "Company Profile", Building2],
  ["/recruiter/jobs/new", "Create Job", PlusCircle],
  ["/recruiter/jobs", "Manage Jobs", Briefcase],
  ["/recruiter/applicants", "Applicants", Users],
  ["/recruiter/ranking", "Candidate Ranking", ListOrdered],
];

export default function RecruiterLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
      isActive ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
    }`;

  const sidebar = (
    <>
      <div className="flex items-center gap-2.5 px-5 py-5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-sm font-extrabold text-navy-900">C</span>
        <span className="text-lg font-extrabold tracking-tight text-white">
          CampusLens <span className="text-brand-400">AI</span>
        </span>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3">
        {NAV.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} end onClick={() => setOpen(false)} className={linkClass}>
            <Icon size={18} /> {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 p-3">
        <button
          onClick={() => { logout(); navigate("/"); }}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-400 hover:bg-white/5 hover:text-white"
        >
          <LogOut size={18} /> Logout
        </button>
      </div>
    </>
  );

  return (
    <ToastProvider>
      <div className="min-h-screen bg-slate-50 lg:pl-64">
        <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-navy-900 lg:flex">{sidebar}</aside>

        {open && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
            <aside className="absolute inset-y-0 left-0 flex w-64 flex-col bg-navy-900">
              <button className="absolute right-3 top-4 text-slate-300" onClick={() => setOpen(false)} aria-label="Close menu">
                <X size={20} />
              </button>
              {sidebar}
            </aside>
          </div>
        )}

        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur-md sm:px-6">
          <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu size={22} />
          </button>
          <span className="hidden text-sm font-medium text-slate-500 lg:block">Recruiter workspace</span>
          <span className="truncate text-sm text-slate-600">{user?.email}</span>
        </header>

        <main className="mx-auto max-w-6xl p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </ToastProvider>
  );
}