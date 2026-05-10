import { useEffect, useMemo, useState } from "react";
import { api, Task } from "../api";

const STATUS_COLOR: Record<string, string> = {
  not_started: "bg-slate-300",
  in_progress: "bg-blue-500",
  blocked: "bg-rose-500",
  done: "bg-emerald-500",
};

function dayDiff(a: Date, b: Date) { return Math.round((+b - +a) / 86400000); }

async function downloadCsv(fmt: "csv" | "json") {
  const url = `/exports/tasks${fmt === "json" ? "?format=json" : ""}`;
  const res = await api.get(url, { responseType: "blob" });
  const mime = fmt === "json" ? "application/json" : "text/csv";
  const blob = new Blob([res.data], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `sj_tasks_${new Date().toISOString().slice(0, 10)}.${fmt}`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function GanttPage({ projectId }: { projectId: number }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [dlBusy, setDlBusy] = useState<string | null>(null);

  useEffect(() => {
    api.get<Task[]>(`/projects/${projectId}/tasks`).then(r => setTasks(r.data));
  }, [projectId]);

  const { start, end, days } = useMemo(() => {
    const dates = tasks.flatMap(t => [t.start_date, t.due_date].filter(Boolean) as string[]);
    if (dates.length === 0) {
      const today = new Date(); today.setHours(0,0,0,0);
      const e = new Date(today); e.setDate(e.getDate() + 30);
      return { start: today, end: e, days: 30 };
    }
    const ds = dates.map(d => new Date(d)).sort((a,b) => +a - +b);
    const s = new Date(ds[0]); s.setDate(s.getDate() - 2);
    const e = new Date(ds[ds.length - 1]); e.setDate(e.getDate() + 4);
    return { start: s, end: e, days: dayDiff(s, e) };
  }, [tasks]);

  const today = new Date(); today.setHours(0,0,0,0);
  const todayOffset = dayDiff(start, today);

  const dl = async (fmt: "csv" | "json") => {
    setDlBusy(fmt);
    try { await downloadCsv(fmt); } finally { setDlBusy(null); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          Live plan timeline · bars colour-coded by status · dotted line = today
        </p>
        <div className="flex gap-2">
          <button
            className="btn-primary text-xs"
            disabled={!!dlBusy}
            onClick={() => dl("csv")}
          >
            {dlBusy === "csv" ? "Downloading…" : "⬇ Export CSV"}
          </button>
          <button
            className="btn-ghost text-xs"
            disabled={!!dlBusy}
            onClick={() => dl("json")}
          >
            {dlBusy === "json" ? "Downloading…" : "⬇ Export JSON"}
          </button>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <div className="min-w-[900px]">
          <div className="grid" style={{ gridTemplateColumns: "260px 1fr" }}>
            <div className="font-medium text-xs text-slate-500 pb-1">Task</div>
            <div className="relative h-6">
              {Array.from({ length: Math.ceil(days / 7) + 1 }).map((_, i) => {
                const d = new Date(start); d.setDate(d.getDate() + i * 7);
                return (
                  <div key={i} className="absolute text-[10px] text-slate-400"
                       style={{ left: `${(i*7/days)*100}%` }}>
                    {d.toISOString().slice(5, 10)}
                  </div>
                );
              })}
            </div>
          </div>

          {tasks.map(t => {
            const s = t.start_date ? new Date(t.start_date) : null;
            const e = t.due_date ? new Date(t.due_date) : null;
            const so = s ? Math.max(0, dayDiff(start, s)) : 0;
            const eo = e ? dayDiff(start, e) : so + 2;
            const left = (so / days) * 100;
            const width = Math.max(1, ((eo - so) / days) * 100);
            const cls = STATUS_COLOR[t.status] || "bg-slate-300";
            return (
              <div key={t.id} className="grid items-center" style={{ gridTemplateColumns: "260px 1fr" }}>
                <div className="text-xs py-1.5 pr-3 truncate">
                  <span className="font-mono text-slate-400 mr-2">{t.code}</span>{t.title}
                </div>
                <div className="relative h-6 border-t border-slate-100">
                  {todayOffset >= 0 && todayOffset <= days && (
                    <div className="absolute top-0 bottom-0 border-l-2 border-dashed border-blue-400"
                         style={{ left: `${(todayOffset/days)*100}%` }} />
                  )}
                  {(s || e) && (
                    <div className={`absolute top-1 h-4 rounded ${cls}`}
                         style={{ left: `${left}%`, width: `${width}%` }}
                         title={`${t.code} • ${t.start_date ?? "?"} → ${t.due_date ?? "?"}`} />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex gap-3 mt-4 text-xs text-slate-500">
          <span><span className="inline-block w-3 h-3 rounded bg-slate-300 mr-1" />not started</span>
          <span><span className="inline-block w-3 h-3 rounded bg-blue-500 mr-1" />in progress</span>
          <span><span className="inline-block w-3 h-3 rounded bg-rose-500 mr-1" />blocked</span>
          <span><span className="inline-block w-3 h-3 rounded bg-emerald-500 mr-1" />done</span>
        </div>
      </div>
    </div>
  );
}
