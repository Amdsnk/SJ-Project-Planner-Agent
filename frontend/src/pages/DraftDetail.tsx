import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, Draft, DraftItem } from "../api";
import { ActionPill, PriorityPill, StatusPill } from "../components/Pills";
import { useAuth } from "../auth";

type EditMap = Record<number, Partial<DraftItem>>;

export default function DraftDetail({ projectId }: { projectId: number }) {
  const { id } = useParams();
  const { user } = useAuth();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [reviewer, setReviewer] = useState("");
  const [edits, setEdits] = useState<EditMap>({});
  const nav = useNavigate();

  useEffect(() => {
    api.get<Draft>(`/projects/${projectId}/drafts/${id}`).then(r => {
      setDraft(r.data);
      setSelected(new Set(r.data.items.filter(i => i.action !== "conflict").map(i => i.id)));
    });
  }, [projectId, id]);

  useEffect(() => {
    if (user?.email && !reviewer) setReviewer(user.email);
  }, [user]);

  if (!draft) return <p className="text-slate-500">Loading…</p>;

  const toggle = (iid: number) => {
    const s = new Set(selected);
    s.has(iid) ? s.delete(iid) : s.add(iid);
    setSelected(s);
  };

  const patch = (iid: number, field: keyof DraftItem, value: string) =>
    setEdits(e => ({ ...e, [iid]: { ...e[iid], [field]: value } }));

  const approve = async () => {
    await api.post(`/projects/${projectId}/drafts/${draft.id}/approve`, {
      decided_by: reviewer,
      accepted_item_ids: Array.from(selected),
      rejected_item_ids: draft.items.filter(i => !selected.has(i.id)).map(i => i.id),
    });
    nav("/drafts");
  };
  const reject = async () => {
    await api.post(`/projects/${projectId}/drafts/${draft.id}/reject`, { decided_by: reviewer });
    nav("/drafts");
  };

  const editable = draft.status === "pending";

  const val = (item: DraftItem, field: keyof DraftItem) =>
    (edits[item.id]?.[field] as string) ?? (item[field] as string) ?? "";

  const acceptedCount = selected.size;
  const totalCount = draft.items.length;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2 className="font-semibold">Plan Update Draft #{draft.id}</h2>
            <p className="text-sm text-slate-600 mt-1">{draft.summary}</p>
            <p className="text-xs text-slate-400 mt-1">
              Status: <span className="font-medium">{draft.status}</span> ·
              Created {draft.created_at.slice(0,16).replace("T"," ")}
              {draft.decided_by && <> · Decided by <strong>{draft.decided_by}</strong></>}
            </p>
            {editable && (
              <p className="text-xs text-slate-500 mt-2">
                <strong>{acceptedCount}</strong> of <strong>{totalCount}</strong> items selected for approval.
                Uncheck any item to reject it individually. Edit title, owner, or due date inline before approving.
              </p>
            )}
          </div>
          {editable && (
            <div className="flex flex-col gap-2 items-end shrink-0">
              <input className="border rounded-md px-2 py-1 text-sm w-52" placeholder="Reviewer name or email"
                value={reviewer} onChange={e => setReviewer(e.target.value)} />
              <div className="flex gap-2">
                <button className="btn-primary" onClick={approve}>
                  Approve {acceptedCount > 0 ? `(${acceptedCount})` : ""}
                </button>
                <button className="btn-danger" onClick={reject}>Reject all</button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr>
            {editable && <th className="table-th w-8"></th>}
            <th className="table-th">Action</th>
            <th className="table-th">Code</th>
            <th className="table-th">Title</th>
            <th className="table-th">Owner</th>
            <th className="table-th">Status</th>
            <th className="table-th">Priority</th>
            <th className="table-th">Due date</th>
            <th className="table-th">Confidence</th>
            <th className="table-th">Evidence &amp; rationale</th>
          </tr></thead>
          <tbody>
            {draft.items.map(it => {
              const rejected = editable && !selected.has(it.id);
              return (
                <tr key={it.id} className={rejected ? "opacity-40 bg-slate-50" : ""}>
                  {editable && (
                    <td className="table-td">
                      <input type="checkbox" checked={selected.has(it.id)}
                        onChange={() => toggle(it.id)} />
                    </td>
                  )}
                  <td className="table-td"><ActionPill s={it.action} /></td>
                  <td className="table-td font-mono text-xs">{it.task_code}</td>

                  {/* Editable title */}
                  <td className="table-td max-w-xs">
                    {editable ? (
                      <input
                        className="border-b border-slate-200 focus:border-blue-400 outline-none text-sm w-full bg-transparent"
                        value={val(it, "title")}
                        onChange={e => patch(it.id, "title", e.target.value)}
                      />
                    ) : (
                      <span className="font-medium">{it.title}</span>
                    )}
                  </td>

                  {/* Editable owner */}
                  <td className="table-td">
                    {editable ? (
                      <input
                        className="border-b border-slate-200 focus:border-blue-400 outline-none text-sm w-28 bg-transparent"
                        placeholder="—"
                        value={val(it, "owner")}
                        onChange={e => patch(it.id, "owner", e.target.value)}
                      />
                    ) : (
                      it.owner || <span className="text-slate-400">—</span>
                    )}
                  </td>

                  <td className="table-td">
                    {it.status ? <StatusPill s={it.status} /> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="table-td">
                    {it.priority ? <PriorityPill s={it.priority} /> : <span className="text-slate-400">—</span>}
                  </td>

                  {/* Editable due date */}
                  <td className="table-td font-mono text-xs">
                    {editable ? (
                      <input
                        type="date"
                        className="border-b border-slate-200 focus:border-blue-400 outline-none text-xs bg-transparent"
                        value={val(it, "due_date")}
                        onChange={e => patch(it.id, "due_date", e.target.value)}
                      />
                    ) : (
                      it.due_date || "—"
                    )}
                  </td>

                  <td className="table-td">
                    <div className="h-1.5 w-24 bg-slate-100 rounded">
                      <div
                        className={"h-1.5 rounded " + (it.confidence >= 0.7 ? "bg-emerald-500" : it.confidence >= 0.5 ? "bg-amber-500" : "bg-rose-500")}
                        style={{ width: `${Math.min(100, it.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500">{(it.confidence * 100).toFixed(0)}%</span>
                  </td>

                  <td className="table-td max-w-sm">
                    {it.evidence && (
                      <div className="text-[11px] italic text-slate-600 mb-0.5">
                        "{it.evidence}"
                      </div>
                    )}
                    <div className="text-[11px] text-slate-500">{it.rationale}</div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
