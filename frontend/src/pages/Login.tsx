import { FormEvent, useState } from "react";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const DEMO_EMAIL = "admin" + "@" + "sj-planner.local";
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState("ChangeMe!123");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await login(email, password);
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form onSubmit={submit} className="bg-white rounded-xl shadow-md w-96 p-8 space-y-4 border border-slate-200">
        <div>
          <h1 className="text-xl font-semibold">
            <span className="text-sj-700">SJ</span> Project Planner Agent
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Agentic AI for task-progress &amp; project tracking
          </p>
        </div>

        <label className="block">
          <span className="text-xs font-medium text-slate-600">Email</span>
          <input className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
                 type="email" value={email} onChange={e => setEmail(e.target.value)} required />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-slate-600">Password</span>
          <input className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
                 type="password" value={password} onChange={e => setPassword(e.target.value)} required />
        </label>

        {err && <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded p-2">{err}</p>}

        <button type="submit" disabled={busy} className="btn-primary w-full">
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <div className="text-[11px] text-slate-500 leading-snug pt-2 border-t border-slate-100">
          <strong>Demo credentials</strong> are pre-filled. In production, sign in with
          Microsoft Entra ID by configuring <code>ENTRA_TENANT_ID</code> and
          <code> ENTRA_CLIENT_ID</code>.
        </div>
      </form>
    </div>
  );
}
