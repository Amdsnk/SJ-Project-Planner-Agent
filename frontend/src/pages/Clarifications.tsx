import { useEffect, useState } from "react";
import { api, Clarification } from "../api";

export default function Clarifications({ projectId }: { projectId: number }) {
  const [items, setItems] = useState<Clarification[]>([]);
  const [filter, setFilter] = useState<"open" | "answered" | "dismissed" | "all">("open");
  const [draft, setDraft] = useState<Record<number, string>>({});

  const load = () => {
    const q = filter === "all" ? "" : `?status=${filter}`;
    api.get<Clarification[]>(`/projects/${projectId}/clarifications${q}`).then(r => setItems(r.data));
  };
  useEffect(load, [projectId, filter]);

  const answer = async (c: Clarification) => {
    const text = (draft[c.id] || "").trim();
    if (!text) return;
    await api.post(`/projects/${projectId}/clarifications/${c.id}/answer`, { answer: text });
    setDraft(d => ({ ...d, [c.id]: "" }));
    load();
  };
  const dismiss = async (c: Clarification) => {
    await api.post(`/projects/${projectId}/clarifications/${c.id}/dismiss`);
    load();
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {(["open","answered","dismissed","all"] as const).map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={(filter === s ? "btn-primary" : "btn-ghost") + " text-xs"}>
            {s}
          </button>
        ))}
      </div>
      <div className="space-y-3">
        {items.map(c => (
          <div key={c.id} className="card">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <p className="font-medium">{c.question}</p>
                <p className="text-xs text-slate-500 mt-1 whitespace-pre-line">{c.context}</p>
                {c.answer && (
                  <p className="text-sm text-emerald-700 mt-2">
                    <strong>Answer:</strong> {c.answer}
                  </p>
                )}
              </div>
              <span className="pill bg-slate-100 text-slate-600">{c.status}</span>
            </div>
            {c.status === "open" && (
              <div className="flex gap-2 mt-3">
                <input className="border rounded-md px-2 py-1 text-sm flex-1"
                  placeholder="Your answer…"
                  value={draft[c.id] || ""}
                  onChange={e => setDraft(d => ({ ...d, [c.id]: e.target.value }))}
                  onKeyDown={e => e.key === "Enter" && answer(c)} />
                <button className="btn-primary text-xs" onClick={() => answer(c)}>Submit</button>
                <button className="btn-ghost text-xs" onClick={() => dismiss(c)}>Dismiss</button>
              </div>
            )}
          </div>
        ))}
        {items.length === 0 && (
          <p className="text-sm text-slate-500">No clarifications in this view.</p>
        )}
      </div>
    </div>
  );
}
