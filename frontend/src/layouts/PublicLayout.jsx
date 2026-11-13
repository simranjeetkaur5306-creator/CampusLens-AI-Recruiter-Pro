import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Activity, Brain, ChevronDown, FileSearch, ListOrdered, Menu, MessageSquare, ShieldCheck, Target, X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { homeFor } from "../utils/routes";

const platformItems = [
  { icon: FileSearch, title: "Resume intelligence", text: "PDF and DOCX parsed into structured skills.", to: "/#matching" },
  { icon: Brain, title: "Semantic matching", text: "Embeddings, cosine similarity, pgvector.", to: "/#matching" },
  { icon: ListOrdered, title: "Candidate ranking", text: "Ranked applicants with explanations.", to: "/#ranking" },
  { icon: Target, title: "Skill-gap analysis", text: "Matched, partial and missing skills.", to: "/#skill-gap" },
  { icon: MessageSquare, title: "AI interview prep", text: "Role and profile based questions.", to: "/#interview" },
  { icon: Activity, title: "Recruitment analytics", text: "Insights from real hiring data.", to: "/#features" },
];

function Brand({ light = false }) {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy-900 text-sm font-extrabold text-white ring-2 ring-brand-500/40">C</span>
      <span className={`text-lg font-extrabold tracking-tight ${light ? "text-white" : "text-navy-900"}`}>
        CampusLens <span className="text-brand-500">AI</span>
      </span>
    </Link>
  );
}

export default function PublicLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { hash, pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mega, setMega] = useState(false);

  // Smooth scroll to #section after route change, otherwise scroll to top.
  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) el.scrollIntoView({ behavior: "smooth" });
    } else {
      window.scrollTo(0, 0);
    }
  }, [hash, pathname]);

  const closeAll = () => { setMobileOpen(false); setMega(false); };

  const navLink = ({ isActive }) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive ? "text-brand-700" : "text-slate-700 hover:bg-slate-100 hover:text-navy-900"
    }`;
  const plainLink = "rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-navy-900";

  const authButtons = user ? (
    <>
      <Link onClick={closeAll} to={homeFor(user.role)} className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800">
        Dashboard
      </Link>
      <button onClick={() => { closeAll(); logout(); navigate("/"); }} className={plainLink}>Logout</button>
    </>
  ) : (
    <>
      <NavLink onClick={closeAll} to="/login" className={navLink}>Login</NavLink>
      <Link onClick={closeAll} to="/register/candidate" className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-navy-800">
        Get started
      </Link>
    </>
  );

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <Brand />

          <nav className="hidden items-center gap-1 lg:flex">
            <div
              className="relative"
              onMouseEnter={() => setMega(true)}
              onMouseLeave={() => setMega(false)}
              onKeyDown={(e) => e.key === "Escape" && setMega(false)}
            >
              <button
                type="button"
                aria-expanded={mega}
                onClick={() => setMega(!mega)}
                className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 hover:text-navy-900"
              >
                Platform <ChevronDown size={16} className={`transition ${mega ? "rotate-180" : ""}`} />
              </button>
              {mega && (
                <div className="absolute left-0 top-full w-[44rem] pt-3">
                  <div className="grid grid-cols-5 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-navy-900/10">
                    <div className="col-span-3 grid gap-1 p-3 sm:grid-cols-2">
                      {platformItems.map(({ icon: Icon, title, text, to }) => (
                        <Link key={title} to={to} onClick={closeAll} className="flex gap-3 rounded-xl p-3 hover:bg-brand-50">
                          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                            <Icon size={18} />
                          </span>
                          <span>
                            <span className="block text-sm font-semibold text-navy-900">{title}</span>
                            <span className="block text-xs text-slate-500">{text}</span>
                          </span>
                        </Link>
                      ))}
                    </div>
                    <div className="col-span-2 flex flex-col justify-between bg-navy-900 p-6 text-white">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-brand-300">Get started</p>
                        <p className="mt-2 text-sm text-slate-300">Choose your workspace and explore the full workflow.</p>
                      </div>
                      <div className="mt-5 space-y-2">
                        <Link onClick={closeAll} to="/register/candidate" className="block rounded-lg bg-white px-3 py-2 text-center text-sm font-semibold text-navy-900 hover:bg-brand-50">For candidates</Link>
                        <Link onClick={closeAll} to="/register/recruiter" className="block rounded-lg border border-white/30 px-3 py-2 text-center text-sm font-semibold hover:bg-white/10">For recruiters</Link>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <Link to="/register/candidate" className={plainLink}>For candidates</Link>
            <Link to="/register/recruiter" className={plainLink}>For recruiters</Link>
            <Link to="/#responsible-ai" className={plainLink}>Responsible AI</Link>
            <NavLink to="/about" className={navLink}>About</NavLink>
          </nav>

          <div className="hidden items-center gap-2 lg:flex">{authButtons}</div>

          <button className="lg:hidden" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle menu">
            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {mobileOpen && (
          <nav className="max-h-[80vh] space-y-1 overflow-y-auto border-t border-slate-200 bg-white px-4 py-4 lg:hidden">
            <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Platform</p>
            {platformItems.map(({ title, to }) => (
              <Link key={title} to={to} onClick={closeAll} className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">{title}</Link>
            ))}
            <div className="my-2 border-t border-slate-100" />
            <Link to="/register/candidate" onClick={closeAll} className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">For candidates</Link>
            <Link to="/register/recruiter" onClick={closeAll} className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">For recruiters</Link>
            <Link to="/#responsible-ai" onClick={closeAll} className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">Responsible AI</Link>
            <Link to="/about" onClick={closeAll} className="block rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">About</Link>
            <div className="flex items-center gap-3 pt-3">{authButtons}</div>
          </nav>
        )}
      </header>

      <main className="flex-1"><Outlet /></main>

      <footer className="bg-navy-950 text-slate-300">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-4 lg:px-8">
          <div className="md:col-span-2">
            <Brand light />
            <p className="mt-4 max-w-sm text-sm text-slate-400">
              AI-assisted recruitment and career recommendation. Rankings and summaries support human decisions; they never replace them.
            </p>
          </div>
          <div className="text-sm">
            <h4 className="font-semibold text-white">Platform</h4>
            <ul className="mt-4 space-y-2 text-slate-400">
              <li><Link to="/#matching" className="hover:text-white">Semantic matching</Link></li>
              <li><Link to="/#ranking" className="hover:text-white">Candidate ranking</Link></li>
              <li><Link to="/#skill-gap" className="hover:text-white">Skill-gap analysis</Link></li>
              <li><Link to="/#interview" className="hover:text-white">AI interview prep</Link></li>
            </ul>
          </div>
          <div className="text-sm">
            <h4 className="font-semibold text-white">Project</h4>
            <ul className="mt-4 space-y-2 text-slate-400">
              <li><Link to="/about" className="hover:text-white">About</Link></li>
              <li><Link to="/register/candidate" className="hover:text-white">Candidate sign up</Link></li>
              <li><Link to="/register/recruiter" className="hover:text-white">Recruiter sign up</Link></li>
              <li>ACEAR, Kurukshetra University</li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 py-5 text-center text-xs text-slate-500">
          © {new Date().getFullYear()} CampusLens AI · Final-year B.Tech (AI &amp; ML) project · Academic year 2026–2027
        </div>
      </footer>
    </div>
  );
}