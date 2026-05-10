import { useEffect, useState } from "react";
import { api, Task } from "../api";
import { PriorityPill, StatusPill } from "../components/Pills";

export default function Tasks({ projectId }: { projectId: number }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<string>("");

  const load = () => api.get<Task[]>(`/projects/${projectId}/tasks`).then(r => setTasks(r.data));
  useEffect(() => { load(); }, [projectId]);

  const filtered = tasks.filter(t =>
    !filter || (t.title + t.code + t.owner).toLowerCase().includes(filter.toLowerCase())
  );

  const update = async (t: Task, patch: Partial<Task>) => {
    await api.patch(`/projects/${projectId}/tasks/${t.id}`, patch);
    load();
  };
  const remove = async (t: Task) => {
    if (!confirm(`Delete ${t.code} "${t.title}"?`)) return;
    await api.delete(`/projects/${projectId}/tasks/${t.id}`);
    load();
  };

  return (
    <div className="space-y-4">
      <input
        className="border border-slate-200 rounded-md px-3 py-1.5 text-sm w-full max-w-md"
        placeholder="Filter by code, title, owner…"
        value={filter} onChange={e => setFilter(e.target.value)}
      />
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr>
            <th className="table-th">Code</th><th className="table-th">Task</th>
            <th className="table-th">Owner</th><th className="table-th">Status</th>
            <th className="table-th">Priority</th><th className="table-th">Start</th>
            <th className="table-th">Due</th><th className="table-th">Deps</th>
            <th className="table-th"></th>
          </tr></thead>
          <tbody>
            {filtered.map(t => (
              <tr key={t.id}>
                <td className="table-td font-mono text-xs">{t.code}</td>
                <td className="table-td">{t.title}</td>
                <td className="table-td">
                  <input className="border-b border-transparent focus:border-slate-300 outline-none w-32"
                    defaultValue={t.owner}
                    onBlur={e => e.target.value !== t.owner && update(t, { owner: e.target.value })} />
                </td>
                <td className="table-td">
                  <select className="bg-transparent text-xs" defaultValue={t.status}
                    onChange={e => update(t, { status: e.target.value })}>
                    {["not_started","in_progress","blocked","done"].map(s =>
                      <option key={s} value={s}>{s.replace("_"," ")}</option>)}
                  </select>
                  <div className="mt-0.5"><StatusPill s={t.status} /></div>
                </td>
                <td className="table-td">
                  <select className="bg-transparent text-xs" defaultValue={t.priority}
                    onChange={e => update(t, { priority: e.target.value })}>
                    {["low","medium","high","critical"].map(s =>
                      <option key={s} value={s}>{s}</option>)}
                  </select>
                  <div className="mt-0.5"><PriorityPill s={t.priority} /></div>
                </td>
                <td className="table-td font-mono text-xs">{t.start_date || "—"}</td>
                <td className="table-td font-mono text-xs">{t.due_date || "—"}</td>
                <td className="table-td font-mono text-xs">{t.dependencies || "—"}</td>
                <td className="table-td">
                  <button className="text-xs text-rose-600 hover:underline" onClick={() => remove(t)}>delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
