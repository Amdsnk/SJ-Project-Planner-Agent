import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, MeetingNote } from "../api";

const AGENTS = [
  { name: "Extraction Agent",      desc: "Calling Azure OpenAI gpt-4o-mini via Foundry — parsing action items, owners, due dates…" },
  { name: "Reconciliation Agent",  desc: "Matching extracted items against the live plan — new task vs update vs conflict…" },
  { name: "Clarification Agent",   desc: "Generating targeted questions for ambiguous owners or missing dates…" },
  { name: "Change Detection Agent",desc: "Comparing current plan snapshot against frozen baseline…" },
  { name: "Priority Agent",        desc: "Re-ranking all tasks by urgency, dependency risk, and overdue signals…" },
  { name: "Assignment Agent",      desc: "Suggesting optimal owners based on skills, role, and current workload…" },
  { name: "Draft Compiler",        desc: "Assembling human-review package — nothing touches the plan yet…" },
];

export default function Notes({ projectId }: { projectId: number }) {
  const [notes, setNotes] = useState<MeetingNote[]>([]);
  const [form, setForm] = useState({ source_type: "meeting", title: "", attendees: "", content: "" });
  const [busy, setBusy] = useState(false);
  const [agentStep, setAgentStep] = useState(-1);
  const [expandedNote, setExpandedNote] = useState<number | null>(null);
  const nav = useNavigate();

  const load = () =>
    api.get<MeetingNote[]>(`/projects/${projectId}/notes`).then(r => setNotes(r.data));
  useEffect(() => { load(); }, [projectId]);

  const loadIntoForm = (n: MeetingNote) => {
    setForm({ source_type: n.source_type, title: n.title, attendees: n.attendees, content: n.content });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const runAnimation = (): Promise<void> =>
    new Promise(resolve => {
      let step = 0;
      setAgentStep(0);
      const tick = () => {
        step += 1;
        if (step >= AGENTS.length) { resolve(); return; }
        setAgentStep(step);
        setTimeout(tick, 420);
      };
      setTimeout(tick, 420);
    });

  const submit = async () => {
    if (!form.content.trim()) return;
    setBusy(true);
    setAgentStep(0);
    try {
      const created = await api.post<MeetingNote>(`/projects/${projectId}/notes`, {
        project_id: projectId, ...form,
      });
      const [draftRes] = await Promise.all([
        api.post(`/projects/${projectId}/notes/${created.data.id}/process`),
        runAnimation(),
      ]);
      nav(`/drafts/${(draftRes.data as any).id}`);
    } finally {
      setBusy(false);
      setAgentStep(-1);
    }
  };

  const reprocess = async (n: MeetingNote) => {
    setBusy(true);
    setAgentStep(0);
    try {
      const [draftRes] = await Promise.all([
        api.post(`/projects/${projectId}/notes/${n.id}/process`),
        runAnimation(),
      ]);
      nav(`/drafts/${(draftRes.data as any).id}`);
    } finally {
      setBusy(false);
      setAgentStep(-1);
    }
  };

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="card space-y-3">
          <h2 className="font-semibold">Ingest meeting note / email / chat</h2>
          <p className="text-xs text-slate-500">
            Paste raw content or load an existing note from the list. The 7-agent pipeline
            (Extraction → Reconciliation → Clarification → Change Detection → Priority →
            Assignment → Draft Compiler) produces a Plan Update Draft for human review.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <select className="border rounded-md px-2 py-1 text-sm"
              value={form.source_type} onChange={e => setForm({ ...form, source_type: e.target.value })}>
              <option value="meeting">Meeting</option>
              <option value="email">Email</option>
              <option value="chat">Chat</option>
            </select>
            <input className="border rounded-md px-2 py-1 text-sm" placeholder="Title"
              value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          </div>
          <input className="border rounded-md px-2 py-1 text-sm w-full"
            placeholder="Attendees / participants"
            value={form.attendees} onChange={e => setForm({ ...form, attendees: e.target.value })} />
          <textarea className="border rounded-md px-2 py-2 text-sm w-full font-mono" rows={12}
            placeholder="Paste meeting minutes, email body, or chat transcript…"
            value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} />
          <button className="btn-primary w-full" disabled={busy} onClick={submit}>
            {busy ? "Running agents…" : "Process → Run 7-Agent Pipeline"}
          </button>
        </div>

        {busy && agentStep >= 0 && (
          <div className="card space-y-2">
            <p className="text-xs font-semibold text-slate-600 mb-1">
              Microsoft Agent Framework — Sequential + Parallel Pipeline
            </p>
            {AGENTS.map((a, i) => {
              const done = i < agentStep;
              const active = i === agentStep;
              return (
                <div key={a.name} className={`flex items-start gap-2 rounded-md px-3 py-2 text-xs transition-all
                  ${done ? "bg-emerald-50 text-emerald-800" : active ? "bg-blue-50 text-blue-800 animate-pulse" : "text-slate-400"}`}>
                  <span className="mt-0.5 shrink-0 text-sm leading-none">
                    {done ? "✓" : active ? "▶" : "○"}
                  </span>
                  <div>
                    <div className="font-semibold">{a.name}</div>
                    {(done || active) && <div className="text-[11px] mt-0.5 opacity-80">{a.desc}</div>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3">Source notes in this project</h2>
        <table className="w-full text-sm">
          <thead><tr>
            <th className="table-th">When</th>
            <th className="table-th">Type</th>
            <th className="table-th">Title</th>
            <th className="table-th"></th>
          </tr></thead>
          <tbody>
            {notes.map(n => (
              <Fragment key={n.id}>
                <tr className="cursor-pointer hover:bg-slate-50"
                  onClick={() => setExpandedNote(expandedNote === n.id ? null : n.id)}>
                  <td className="table-td font-mono text-xs">{n.occurred_at?.slice(0,10)}</td>
                  <td className="table-td">
                    <span className="pill bg-slate-100 text-slate-700">{n.source_type}</span>
                  </td>
                  <td className="table-td">
                    <div className="font-medium">{n.title}</div>
                    <div className="text-[11px] text-slate-500 truncate max-w-xs">
                      {n.content.slice(0, 100)}…
                    </div>
                  </td>
                  <td className="table-td">
                    <div className="flex flex-col gap-1">
                      <button className="btn-primary text-xs" disabled={busy}
                        onClick={e => { e.stopPropagation(); reprocess(n); }}>
                        Process
                      </button>
                      <button className="btn-ghost text-xs"
                        onClick={e => { e.stopPropagation(); loadIntoForm(n); }}>
                        Load
                      </button>
                    </div>
                  </td>
                </tr>
                {expandedNote === n.id && (
                  <tr>
                    <td colSpan={4} className="px-3 pb-3">
                      <div className="bg-slate-50 border border-slate-200 rounded-md p-3">
                        {n.attendees && (
                          <p className="text-[11px] text-slate-500 mb-2">
                            <strong>Attendees:</strong> {n.attendees}
                          </p>
                        )}
                        <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed">
                          {n.content}
                        </pre>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {notes.length === 0 && (
              <tr><td colSpan={4} className="text-center text-sm text-slate-500 py-6">
                No notes yet — paste one above and click Process.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
