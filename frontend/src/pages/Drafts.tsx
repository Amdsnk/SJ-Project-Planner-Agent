import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Draft } from "../api";

const STATUS: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-slate-200 text-slate-600",
};

export default function Drafts({ projectId }: { projectId: number }) {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  useEffect(() => {
    api.get<Draft[]>(`/projects/${projectId}/drafts`).then(r => setDrafts(r.data));
  }, [projectId]);

  return (
    <div className="card">
      <p className="text-xs text-slate-500 mb-3">
        Each draft is a proposed change set extracted from a single source. A
        human reviewer must approve before it touches the official plan.
      </p>
      <table className="w-full text-sm">
        <thead><tr>
          <th className="table-th">When</th>
          <th className="table-th">Status</th>
          <th className="table-th">Items</th>
          <th className="table-th">Summary</th>
          <th className="table-th">Decided by</th>
          <th className="table-th"></th>
        </tr></thead>
        <tbody>
          {drafts.map(d => (
            <tr key={d.id}>
              <td className="table-td font-mono text-xs">{d.created_at.slice(0,16).replace("T"," ")}</td>
              <td className="table-td"><span className={"pill " + (STATUS[d.status] ?? "")}>{d.status}</span></td>
              <td className="table-td">{d.items.length}</td>
              <td className="table-td max-w-md">{d.summary}</td>
              <td className="table-td text-xs text-slate-500">{d.decided_by || "—"}</td>
              <td className="table-td">
                <Link to={`/drafts/${d.id}`} className="btn-primary text-xs">Review</Link>
              </td>
            </tr>
          ))}
          {drafts.length === 0 && (
            <tr><td colSpan={6} className="text-center text-sm text-slate-500 py-6">
              No drafts yet — ingest a meeting note to generate one.
            </td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
