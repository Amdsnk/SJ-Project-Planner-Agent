const STATUS: Record<string, string> = {
  not_started: "bg-slate-100 text-slate-700",
  in_progress: "bg-blue-100 text-blue-700",
  blocked: "bg-rose-100 text-rose-700",
  done: "bg-emerald-100 text-emerald-700",
};
const PRIORITY: Record<string, string> = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-rose-100 text-rose-700",
};
const ACTION: Record<string, string> = {
  create: "bg-emerald-100 text-emerald-700",
  update: "bg-blue-100 text-blue-700",
  conflict: "bg-amber-100 text-amber-700",
};
const SEVERITY: Record<string, string> = {
  info: "bg-slate-100 text-slate-700",
  minor: "bg-amber-100 text-amber-700",
  major: "bg-rose-100 text-rose-700",
};

export const StatusPill = ({ s }: { s: string }) => (
  <span className={"pill " + (STATUS[s] || "bg-slate-100 text-slate-700")}>
    {s.replace("_", " ") || "—"}
  </span>
);
export const PriorityPill = ({ s }: { s: string }) => (
  <span className={"pill " + (PRIORITY[s] || "bg-slate-100 text-slate-700")}>
    {s || "—"}
  </span>
);
export const ActionPill = ({ s }: { s: string }) => (
  <span className={"pill " + (ACTION[s] || "bg-slate-100 text-slate-700")}>{s}</span>
);
export const SeverityPill = ({ s }: { s: string }) => (
  <span className={"pill " + (SEVERITY[s] || "bg-slate-100 text-slate-700")}>{s}</span>
);
