import { useEffect, useState } from "react";
import { api, ChangeLogRow, DiffReport } from "../api";
import { SeverityPill } from "../components/Pills";

export default function Changes({ projectId }: { projectId: number }) {
  const [log, setLog] = useState<ChangeLogRow[]>([]);
  const [diff, setDiff] = useState<DiffReport | null>(null);

  const load = () => {
    api.get<ChangeLogRow[]>(`/projects/${projectId}/changes`).then(r => setLog(r.data));
    api.get<DiffReport>(`/projects/${projectId}/changes/diff`).then(r => setDiff(r.data));
  };
  useEffect(load, [projectId]);

  return (
    <div className="space-y-6">
      <div className="card">
        <div>
          <h2 className="font-semibold">What changed vs baseline</h2>
          <p className="text-xs text-slate-500 mt-1">{diff?.summary}</p>
        </div>
        <table className="w-full text-sm mt-3">
          <thead><tr>
            <th className="table-th">Severity</th>
            <th className="table-th">Code</th>
            <th className="table-th">Task</th>
            <th className="table-th">Type</th>
            <th className="table-th">Field</th>
            <th className="table-th">Was</th>
            <th className="table-th">Now</th>
          </tr></thead>
          <tbody>
            {(diff?.items ?? []).map((c, i) => (
              <tr key={i}>
                <td className="table-td"><SeverityPill s={c.severity} /></td>
                <td className="table-td font-mono text-xs">{c.task_code}</td>
                <td className="table-td">{c.title}</td>
                <td className="table-td text-xs text-slate-600">{c.change_type.replace("_"," ")}</td>
                <td className="table-td text-xs text-slate-500">{c.field}</td>
                <td className="table-td text-xs text-slate-500">{c.old_value || "—"}</td>
                <td className="table-td text-xs">{c.new_value || "—"}</td>
              </tr>
            ))}
            {!diff?.items?.length && (
              <tr><td colSpan={7} className="text-center text-sm text-slate-500 py-6">No deltas vs baseline.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3">Change log (audit trail)</h2>
        <table className="w-full text-sm">
          <thead><tr>
            <th className="table-th">When</th>
            <th className="table-th">Code</th>
            <th className="table-th">Field</th>
            <th className="table-th">Was</th>
            <th className="table-th">Now</th>
            <th className="table-th">Source</th>
            <th className="table-th">Actor</th>
            <th className="table-th">Rationale</th>
          </tr></thead>
          <tbody>
            {log.map(r => (
              <tr key={r.id}>
                <td className="table-td font-mono text-xs">{r.created_at.slice(0,16).replace("T"," ")}</td>
                <td className="table-td font-mono text-xs">{r.task_code}</td>
                <td className="table-td text-xs">{r.field}</td>
                <td className="table-td text-xs text-slate-500 max-w-[12rem] truncate">{r.old_value || "—"}</td>
                <td className="table-td text-xs max-w-[12rem] truncate">{r.new_value || "—"}</td>
                <td className="table-td text-xs text-slate-500">{r.source}</td>
                <td className="table-td text-xs">{r.actor}</td>
                <td className="table-td text-xs text-slate-600 max-w-md">{r.rationale}</td>
              </tr>
            ))}
            {log.length === 0 && (
              <tr><td colSpan={8} className="text-center text-sm text-slate-500 py-6">No changes recorded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
