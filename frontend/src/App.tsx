import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, Project } from "./api";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tasks from "./pages/Tasks";
import GanttPage from "./pages/Gantt";
import Notes from "./pages/Notes";
import Drafts from "./pages/Drafts";
import DraftDetail from "./pages/DraftDetail";
import Changes from "./pages/Changes";
import Clarifications from "./pages/Clarifications";
import Exports from "./pages/Exports";

const NAV = [
  { to: "/",               label: "Dashboard" },
  { to: "/tasks",          label: "Tasks" },
  { to: "/gantt",          label: "Gantt" },
  { to: "/notes",          label: "Ingest" },
  { to: "/drafts",         label: "Plan Updates" },
  { to: "/changes",        label: "Changes" },
  { to: "/clarifications", label: "Clarifications" },
  { to: "/exports",        label: "Exports" },
];

export default function App() {
  const { user, token, loading, logout } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const loc = useLocation();

  useEffect(() => {
    if (!token) { setProjects([]); setProject(null); return; }
    api.get<Project[]>("/projects")
      .then(r => {
        setProjects(r.data);
        setProject(prev => {
          if (prev) {
            const still = r.data.find(p => p.id === prev.id);
            return still ?? r.data[0] ?? null;
          }
          return r.data[0] ?? null;
        });
      })
      .catch(() => { setProjects([]); setProject(null); });
  }, [token]);

  if (loading) return <div className="p-8 text-slate-500">Loading…</div>;
  if (!token || !user) return <Login />;
  if (!project) return <div className="p-8 text-slate-500">Loading project…</div>;
  const pid = project.id;

  const activeLabel = NAV.find(n =>
    n.to === loc.pathname ||
    (n.to !== "/" && loc.pathname.startsWith(n.to))
  )?.label ?? "Dashboard";

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-sj-900 text-white p-5 flex flex-col">
        <Link to="/" className="text-lg font-bold tracking-tight">
          <span className="text-sj-100">SJ</span> Planner Agent
        </Link>

        {projects.length > 1 ? (
          <select
            value={project.id}
            onChange={e => {
              const p = projects.find(x => x.id === Number(e.target.value));
              if (p) setProject(p);
            }}
            className="mt-2 mb-5 w-full rounded-md bg-sj-700 border border-sj-600 text-white text-xs px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-sj-400 truncate"
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        ) : (
          <p className="text-xs text-sj-100/70 mt-1 mb-6 truncate">{project.name}</p>
        )}

        <nav className="space-y-1 flex-1">
          {NAV.map(n => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"}
              className={({ isActive }) =>
                "block px-3 py-2 rounded-md text-sm " +
                (isActive ? "bg-sj-700 text-white" : "text-sj-100/80 hover:bg-sj-700/50")
              }>
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-6 pt-3 border-t border-sj-700/50">
          <div className="text-[11px] text-sj-100/70 leading-snug">
            Signed in as
            <div className="text-white text-xs font-medium truncate">{user.email}</div>
            <div className="text-sj-100/60 text-[10px] uppercase">{user.role}</div>
          </div>
          <button onClick={logout}
            className="mt-2 text-[11px] text-sj-100/70 hover:text-white underline">
            Sign out
          </button>
        </div>
        <div className="text-[11px] text-sj-100/50 mt-4 leading-snug">
          Microsoft Agent Framework + Azure OpenAI / Foundry compatible.
        </div>
      </aside>

      <main className="flex-1 p-8 overflow-x-auto">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">{activeLabel}</h1>
          <span className="text-sm text-slate-400 font-normal">{project.name}</span>
        </header>
        <Routes>
          <Route path="/"               element={<Dashboard projectId={pid} />} />
          <Route path="/tasks"          element={<Tasks projectId={pid} />} />
          <Route path="/gantt"          element={<GanttPage projectId={pid} />} />
          <Route path="/notes"          element={<Notes projectId={pid} />} />
          <Route path="/drafts"         element={<Drafts projectId={pid} />} />
          <Route path="/drafts/:id"     element={<DraftDetail projectId={pid} />} />
          <Route path="/changes"        element={<Changes projectId={pid} />} />
          <Route path="/clarifications" element={<Clarifications projectId={pid} />} />
          <Route path="/exports"        element={<Exports />} />
        </Routes>
      </main>
    </div>
  );
}
