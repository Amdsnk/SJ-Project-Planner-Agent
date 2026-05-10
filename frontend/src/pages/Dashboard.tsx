import { useEffect, useState } from "react";
import { api, KPIs, Ranked, Assignment, Task } from "../api";
import { PriorityPill, StatusPill } from "../components/Pills";

async function downloadCsv(endpoint: string, filename: string, format: "csv" | "json" = "csv") {
  const url = `/exports/${endpoint}${format === "json" ? "?format=json" : ""}`;
  const res = await api.get(url, { responseType: "blob" });
  const mime = format === "json" ? "application/json" : "text/csv";
  const blob = new Blob([res.data], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function Dashboard({ projectId }: { projectId: number }) {
  const [k, setK] = useState<KPIs | null>(null);
  const [ranked, setRanked] = useState<Ranked[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [sugg, setSugg] = useState<Assignment[]>([]);
  const [llm, setLlm] = useState<boolean>(false);
  const [dlBusy, setDlBusy] = useState<string | null>(null);

  useEffect(() => {
    api.get<KPIs>(`/projects/${projectId}/dashboard`).then(r => setK(r.data));
    api.get<Ranked[]>(`/projects/${projectId}/priority`).then(r => setRanked(r.data));
    api.get<Task[]>(`/projects/${projectId}/tasks`).then(r => setTasks(r.data));
    api.get<Assignment[]>(`/projects/${projectId}/assignments`).then(r => setSugg(r.data));
    api.get("/health").then(r => setLlm(!!r.data.llm_enabled));
  }, [projectId]);

  if (!k) return <p className="text-slate-500">Loading…</p>;

  const dl = async (fmt: "csv" | "json") => {
    const tag = `tasks_${fmt}`;
    setDlBusy(tag);
    const date = new Date().toISOString().slice(0, 10);
    try {
      await downloadCsv("tasks", `sj_tasks_${date}.${fmt}`, fmt);
    } finally {
      setDlBusy(null);
    }
  };

  const tile = (label: string, value: number, color: string, badge?: "alert" | "warn") => (
    <div className={`card flex flex-col relative ${badge === "alert" ? "ring-1 ring-rose-300" : badge === "warn" ? "ring-1 ring-amber-300" : ""}`}>
      <span className="text-xs uppercase text-slate-500 leading-tight">{label}</span>
      <span className={"text-3xl font-bold mt-1 " + color}>{value}</span>
      {badge === "alert" && value > 0 && (
        <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
      )}
      {badge === "warn" && value > 0 && (
        <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
      )}
    </div>
  );

  const upcoming = tasks
    .filter(t => t.due_date && t.status !== "done")
    .sort((a, b) => (a.due_date || "").localeCompare(b.due_date || ""))
    .slice(0, 6);

  const blocked = tasks.filter(t => t.status === "blocked").slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className={"text-xs px-3 py-1.5 rounded-md inline-block " + (llm ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500")}>
          LLM mode: <strong>{llm ? "Azure OpenAI / Foundry connected" : "deterministic fallback — set AZURE_OPENAI_* to enable Foundry"}</strong>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-primary text-xs"
            disabled={!!dlBusy}
            onClick={() => dl("csv")}
          >
            {dlBusy === "tasks_csv" ? "Downloading…" : "⬇ Export CSV"}
          </button>
          <button
            className="btn-ghost text-xs"
            disabled={!!dlBusy}
            onClick={() => dl("json")}
          >
            {dlBusy === "tasks_json" ? "Downloading…" : "⬇ Export JSON"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-9 gap-3">
        {tile("Tasks", k.total_tasks, "text-slate-900")}
        {tile("Not started", k.not_started, "text-slate-700")}
        {tile("In progress", k.in_progress, "text-blue-700")}
        {tile("Blocked", k.blocked, "text-rose-700", "alert")}
        {tile("Done", k.done, "text-emerald-700")}
        {tile("Overdue", k.overdue, "text-rose-700", "alert")}
        {tile("Due ≤ 7d", k.upcoming_7d, "text-amber-700", "warn")}
        {tile("Pending drafts", k.pending_drafts, "text-sj-700", "warn")}
        {tile("Open clarifications", k.open_clarifications, "text-violet-700", "warn")}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="font-semibold mb-3">Priority Agent — urgency ranking</h2>
          <table className="w-full text-sm">
            <thead><tr>
              <th className="table-th">Score</th>
              <th className="table-th">Code</th>
              <th className="table-th">Task</th>
              <th className="table-th">Why</th>
            </tr></thead>
            <tbody>
              {ranked.slice(0, 8).map(r => (
                <tr key={r.code}>
                  <td className="table-td font-mono font-bold text-rose-700">{r.score.toFixed(1)}</td>
                  <td className="table-td font-mono text-xs text-slate-500">{r.code}</td>
                  <td className="table-td">{r.title}</td>
                  <td className="table-td text-xs text-slate-500">{r.reason}</td>
                </tr>
              ))}
              {ranked.length === 0 && (
                <tr><td colSpan={4} className="text-center text-sm text-slate-400 py-4">No tasks ranked yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h2 className="font-semibold mb-3">Upcoming deadlines</h2>
          <table className="w-full text-sm">
            <thead><tr>
              <th className="table-th">Due</th>
              <th className="table-th">Task</th>
              <th className="table-th">Owner</th>
              <th className="table-th">Status</th>
              <th className="table-th">Priority</th>
            </tr></thead>
            <tbody>
              {upcoming.map(t => (
                <tr key={t.id}>
                  <td className="table-td font-mono text-xs">{t.due_date}</td>
                  <td className="table-td">{t.title}</td>
                  <td className="table-td text-sm">{t.owner || <span className="text-slate-400">—</span>}</td>
                  <td className="table-td"><StatusPill s={t.status} /></td>
                  <td className="table-td"><PriorityPill s={t.priority} /></td>
                </tr>
              ))}
              {upcoming.length === 0 && (
                <tr><td colSpan={5} className="text-center text-sm text-slate-400 py-4">No upcoming deadlines.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {blocked.length > 0 && (
        <div className="card border-rose-200 border">
          <h2 className="font-semibold mb-3 text-rose-700">Blocked items</h2>
          <table className="w-full text-sm">
            <thead><tr>
              <th className="table-th">Code</th>
              <th className="table-th">Task</th>
              <th className="table-th">Owner</th>
              <th className="table-th">Priority</th>
              <th className="table-th">Due</th>
            </tr></thead>
            <tbody>
              {blocked.map(t => (
                <tr key={t.id}>
                  <td className="table-td font-mono text-xs">{t.code}</td>
                  <td className="table-td">{t.title}</td>
                  <td className="table-td text-sm">{t.owner || <span className="text-slate-400">—</span>}</td>
                  <td className="table-td"><PriorityPill s={t.priority} /></td>
                  <td className="table-td font-mono text-xs">{t.due_date || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sugg.length > 0 && (
        <div className="card">
          <h2 className="font-semibold mb-1">Assignment Agent — owner suggestions</h2>
          <p className="text-xs text-slate-500 mb-3">
            Based on role/skill tags + workload heuristics. Requires explicit confirmation before applying.
          </p>
          <table className="w-full text-sm">
            <thead><tr>
              <th className="table-th">Task</th>
              <th className="table-th">Suggested owner</th>
              <th className="table-th">Score</th>
              <th className="table-th">Reason</th>
            </tr></thead>
            <tbody>
              {sugg.map(s => (
                <tr key={s.task_code}>
                  <td className="table-td font-mono text-xs">{s.task_code}</td>
                  <td className="table-td font-medium">{s.suggested_owner}</td>
                  <td className="table-td font-mono">{s.score}</td>
                  <td className="table-td text-xs text-slate-500">{s.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
