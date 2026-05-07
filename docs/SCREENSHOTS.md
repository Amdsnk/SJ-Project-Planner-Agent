# Capturing UI Screenshots for the README & Pitch Deck

Six clean shots are enough for a polished README + 5-min pitch overlay.
Save every PNG into `docs/screenshots/` so the README references resolve.

## 0 — Pre-flight

```powershell
# Backend (with seeded CWB_SJ data + drafts/clarifications already populated)
cd backend
.\.venv\Scripts\python.exe scripts/preload_demo.py
.\.venv\Scripts\activate
uvicorn app.main:app --reload    # http://127.0.0.1:8000

# Frontend (separate shell)
cd frontend
npm install
npm run dev                      # http://127.0.0.1:5173
```

Log in once with `[email protected]` / `ChangeMe!123` so the JWT is cached.

Set the browser to a clean size for consistent crops:
* DevTools → toggle device toolbar → **Responsive 1440 × 900**, zoom **100 %**
* Hide bookmarks bar, close DevTools before capturing.

## 1 — The six shots

| # | URL path | Filename | What to frame |
|---|---|---|---|
| 1 | `/` | `01-dashboard.png` | KPI tiles + recent activity. Scroll to top. |
| 2 | `/tasks` | `02-tasks.png` | Filter input empty; show ≥ 10 tasks; mix of statuses. |
| 3 | `/gantt` | `03-gantt.png` | Pick the project with the longest range so bars span. |
| 4 | `/notes` | `04-notes.png` | Hover the **Process** button on the first unprocessed note. |
| 5 | `/drafts/<id>` | `05-draft-detail.png` | Open a draft with both a `create` and a `conflict` item; expand evidence quote. |
| 6 | `/clarifications` | `06-clarifications.png` | Filter = *open*; show ≥ 3 questions. |

## 2 — Native capture (Windows)

* `Win + Shift + S` → *Rectangle* → drag exactly over the SPA viewport
  (avoid taskbar/title bar) → save as PNG with the filename above.
* Re-crop to **1440 × 850** in any image editor for uniform width.

## 3 — Headless capture (optional, reproducible)

If you want pixel-identical screenshots regenerated on every release, install
Playwright once:

```powershell
cd frontend
npm i -D @playwright/test
npx playwright install chromium
```

Save the snippet below as `frontend/scripts/screenshots.mjs`:

```js
import { chromium } from "@playwright/test";

const SHOTS = [
  ["/",                  "01-dashboard.png"],
  ["/tasks",             "02-tasks.png"],
  ["/gantt",             "03-gantt.png"],
  ["/notes",             "04-notes.png"],
  ["/clarifications",    "06-clarifications.png"],
];

const ctx = await chromium.launch();
const page = await ctx.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://127.0.0.1:5173/login");
await page.fill('input[type="email"]', "[email protected]");
await page.fill('input[type="password"]', "ChangeMe!123");
await page.click('button[type="submit"]');
await page.waitForURL(/\/$/);

for (const [path, file] of SHOTS) {
  await page.goto("http://127.0.0.1:5173" + path);
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: `../docs/screenshots/${file}`, fullPage: false });
  console.log("saved", file);
}
await ctx.close();
```

Run it: `node scripts/screenshots.mjs` (the draft-detail page needs an id, so
shoot it manually).

## 4 — Wire them into the README

Replace the architecture-only image block in `README.md` with:

```md
## 📸 Screens

| Dashboard | Tasks | Gantt |
|---|---|---|
| ![dashboard](docs/screenshots/01-dashboard.png) | ![tasks](docs/screenshots/02-tasks.png) | ![gantt](docs/screenshots/03-gantt.png) |

| Ingest | Plan Update Draft | Clarifications |
|---|---|---|
| ![notes](docs/screenshots/04-notes.png) | ![draft](docs/screenshots/05-draft-detail.png) | ![clarif](docs/screenshots/06-clarifications.png) |
```

(I’ve already added a stub for this in `README.md`, so once the PNGs land in
`docs/screenshots/` the section renders automatically on GitHub.)
