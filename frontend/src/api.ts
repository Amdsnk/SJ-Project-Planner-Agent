import axios from "axios";

export const api = axios.create({ baseURL: "/api" });

// Module-level interceptor: reads token from localStorage on every request so
// there is no race with the AuthProvider effect that was previously installing
// it asynchronously.
api.interceptors.request.use(cfg => {
  const t = localStorage.getItem("sj_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export type Project = { id: number; name: string; description: string };

export type Task = {
  id: number; code: string; title: string; owner: string; status: string;
  priority: string; start_date: string | null; due_date: string | null;
  progress: number; dependencies: string; notes: string; updated_at: string;
};

export type MeetingNote = {
  id: number; project_id: number; source_type: string; title: string;
  attendees: string; occurred_at: string; content: string; processed: boolean;
  created_at: string;
};

export type DraftItem = {
  id: number; action: "create" | "update" | "conflict"; task_code: string;
  title: string; owner: string; status: string; priority: string;
  start_date: string | null; due_date: string | null; dependencies: string;
  confidence: number; evidence: string; rationale: string; accepted: boolean | null;
};

export type Draft = {
  id: number; project_id: number; note_id: number | null; summary: string;
  status: "pending" | "approved" | "rejected"; created_at: string;
  decided_at: string | null; decided_by: string; items: DraftItem[];
};

export type ChangeLogRow = {
  id: number; task_code: string; field: string; old_value: string;
  new_value: string; source: string; actor: string; rationale: string;
  created_at: string;
};

export type DiffItem = {
  task_code: string; title: string; change_type: string; field: string;
  old_value: string; new_value: string; severity: "info" | "minor" | "major";
};
export type DiffReport = {
  project_id: number; generated_at: string; summary: string; items: DiffItem[];
};

export type Clarification = {
  id: number; project_id: number; draft_item_id: number | null; question: string;
  context: string; answer: string; status: "open" | "answered" | "dismissed";
  created_at: string; answered_at: string | null;
};

export type KPIs = {
  total_tasks: number; not_started: number; in_progress: number; blocked: number;
  done: number; overdue: number; upcoming_7d: number;
  pending_drafts: number; open_clarifications: number;
};

export type Ranked = { code: string; title: string; score: number; reason: string };
export type Assignment = { task_code: string; suggested_owner: string; score: number; reason: string };
export type TeamMember = { id: number; name: string; role: string; skills: string; capacity: number };
