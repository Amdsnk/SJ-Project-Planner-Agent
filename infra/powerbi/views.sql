-- =============================================================================
-- SJ Project Planner Agent — Power BI integration views
--
-- Apply against the production Postgres database (the same one the API is
-- pointing at via DATABASE_URL). All views are read-only and respect
-- multi-tenant scoping by exposing org_id so Power BI can apply RLS.
--
-- After applying, point Power BI Desktop at:
--   Server  : <postgres-fqdn>
--   Database: sj_planner
--   Schema  : public  (all v_* views)
--
-- and import the model from ./SJPlannerModel.bim alongside this file.
-- =============================================================================

-- ----- Tasks (current live plan) -----------------------------------------------
CREATE OR REPLACE VIEW v_tasks AS
SELECT
    t.id              AS task_id,
    t.code            AS task_code,
    p.org_id,
    p.id              AS project_id,
    p.name            AS project_name,
    t.title,
    NULLIF(t.owner, '') AS owner,
    t.status,
    t.priority,
    t.start_date,
    t.due_date,
    COALESCE(t.progress, 0)::numeric AS progress,
    t.dependencies,
    CASE WHEN t.due_date IS NOT NULL AND t.due_date < CURRENT_DATE
              AND t.status <> 'done' THEN 1 ELSE 0 END AS is_overdue,
    CASE WHEN t.due_date IS NOT NULL
              AND t.due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
              AND t.status <> 'done' THEN 1 ELSE 0 END AS is_due_within_7d,
    t.updated_at
FROM tasks t
JOIN projects p ON p.id = t.project_id;


-- ----- Baseline plan (for variance analysis) ----------------------------------
CREATE OR REPLACE VIEW v_baseline_tasks AS
SELECT
    b.id              AS baseline_id,
    b.code            AS task_code,
    p.org_id,
    p.id              AS project_id,
    b.title,
    b.owner,
    b.start_date,
    b.due_date,
    b.priority
FROM baseline_tasks b
JOIN projects p ON p.id = b.project_id;


-- ----- Schedule variance (current vs baseline) --------------------------------
CREATE OR REPLACE VIEW v_schedule_variance AS
SELECT
    p.org_id,
    p.id   AS project_id,
    p.name AS project_name,
    COALESCE(t.code, b.task_code) AS task_code,
    COALESCE(t.title, b.title)    AS title,
    b.due_date AS baseline_due,
    t.due_date AS current_due,
    (t.due_date - b.due_date)     AS days_slip,
    CASE
        WHEN t.id IS NULL THEN 'removed'
        WHEN b.baseline_id IS NULL THEN 'added'
        WHEN t.due_date <> b.due_date THEN 'shifted'
        ELSE 'on_baseline'
    END AS variance_type
FROM v_tasks t
FULL OUTER JOIN v_baseline_tasks b
  ON b.project_id = t.project_id AND b.task_code = t.task_code
JOIN projects p ON p.id = COALESCE(t.project_id, b.project_id);


-- ----- Drafts pipeline (PMO funnel) -------------------------------------------
CREATE OR REPLACE VIEW v_drafts AS
SELECT
    d.id              AS draft_id,
    p.org_id,
    p.id              AS project_id,
    p.name            AS project_name,
    d.note_id,
    d.summary,
    d.status,
    d.decided_by,
    d.created_at,
    d.decided_at,
    EXTRACT(EPOCH FROM (d.decided_at - d.created_at))/3600.0 AS hours_to_decision,
    (SELECT COUNT(*) FROM draft_items di WHERE di.draft_id = d.id) AS item_count,
    (SELECT COUNT(*) FROM draft_items di WHERE di.draft_id = d.id AND di.accepted IS TRUE)  AS accepted_count,
    (SELECT COUNT(*) FROM draft_items di WHERE di.draft_id = d.id AND di.accepted IS FALSE) AS rejected_count,
    (SELECT COUNT(*) FROM draft_items di WHERE di.draft_id = d.id AND di.action = 'conflict') AS conflict_count
FROM plan_update_drafts d
JOIN projects p ON p.id = d.project_id;


-- ----- Change-log (audit feed) ------------------------------------------------
CREATE OR REPLACE VIEW v_change_log AS
SELECT
    c.id              AS change_id,
    p.org_id,
    p.id              AS project_id,
    p.name            AS project_name,
    c.task_code,
    c.field,
    c.old_value,
    c.new_value,
    c.source,
    c.actor,
    c.rationale,
    c.created_at
FROM change_log c
JOIN projects p ON p.id = c.project_id;


-- ----- Clarifications backlog -------------------------------------------------
CREATE OR REPLACE VIEW v_clarifications AS
SELECT
    cl.id             AS clarification_id,
    p.org_id,
    p.id              AS project_id,
    p.name            AS project_name,
    cl.draft_item_id,
    cl.question,
    cl.context,
    cl.answer,
    cl.status,
    cl.created_at,
    cl.answered_at,
    EXTRACT(EPOCH FROM (cl.answered_at - cl.created_at))/3600.0 AS hours_to_answer
FROM clarifications cl
JOIN projects p ON p.id = cl.project_id;


-- ----- Notes ingest activity --------------------------------------------------
CREATE OR REPLACE VIEW v_notes AS
SELECT
    n.id              AS note_id,
    p.org_id,
    p.id              AS project_id,
    p.name            AS project_name,
    n.source_type,
    n.title,
    n.attendees,
    n.occurred_at,
    n.processed,
    n.created_at,
    LENGTH(n.content) AS content_length
FROM meeting_notes n
JOIN projects p ON p.id = n.project_id;
