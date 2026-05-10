import { useState } from "react";
import { api } from "../api";

const EXPORTS = [
  { key: "tasks",          label: "Tasks",        desc: "All tasks with status, owner, priority, dates, overdue flags", supportsJson: true },
  { key: "change_log",     label: "Change Log",   desc: "Full audit trail — who changed what, when, and why",          supportsJson: false },
  { key: "drafts",         label: "Plan Drafts",  desc: "All plan update drafts and their decision status",            supportsJson: false },
  { key: "clarifications", label: "Clarifications", desc: "Open and answered clarification questions",                supportsJson: false },
];

async function downloadBlob(endpoint: string, filename: string, format: "csv" | "json") {
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

export default function Exports() {
  const [busy, setBusy] = useState<string | null>(null);

  const dl = async (key: string, format: "csv" | "json") => {
    const tag = `${key}_${format}`;
    setBusy(tag);
    try {
      const ext = format === "json" ? "json" : "csv";
      await downloadBlob(key, `sj_${key}_${new Date().toISOString().slice(0,10)}.${ext}`, format);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="card">
        <p className="text-sm text-slate-600 mb-1">
          All exports are scoped to your organisation and secured with your session token.
          CSV files are ready for Power BI <code className="bg-slate-100 px-1 rounded text-xs">Web.Contents()</code>, Power Query, or Excel.
          JSON is compatible with pandas, Power Automate, and Azure Data Factory.
        </p>
      </div>

      {EXPORTS.map(e => (
        <div key={e.key} className="card flex items-center justify-between gap-4">
          <div className="flex-1">
            <div className="font-semibold text-sm">{e.label}</div>
            <div className="text-xs text-slate-500 mt-0.5">{e.desc}</div>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              className="btn-primary text-xs"
              disabled={!!busy}
              onClick={() => dl(e.key, "csv")}
            >
              {busy === `${e.key}_csv` ? "Downloading…" : "⬇ CSV"}
            </button>
            {e.supportsJson && (
              <button
                className="btn-ghost text-xs"
                disabled={!!busy}
                onClick={() => dl(e.key, "json")}
              >
                {busy === `${e.key}_json` ? "Downloading…" : "⬇ JSON"}
              </button>
            )}
          </div>
        </div>
      ))}

      <div className="card bg-slate-50 border border-slate-200">
        <p className="text-xs text-slate-500 font-medium mb-2">Power BI connection string</p>
        <code className="text-xs bg-white border border-slate-200 rounded px-2 py-1.5 block break-all select-all">
          {`= Csv.Document(Web.Contents("${window.location.origin}/api/exports/tasks", [Headers=[Authorization="Bearer <paste_token_here>"]]), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv])`}
        </code>
        <p className="text-[11px] text-slate-400 mt-1">Replace &lt;paste_token_here&gt; with your JWT from localStorage key <code>sj_token</code>.</p>
      </div>
    </div>
  );
}
