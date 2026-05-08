# Deployment Guide — SJ Project Planner Agent

End-to-end runbook for taking the codebase live. The recommended target is
**Azure Container Apps** (backend) + **Azure Static Web Apps** (frontend) +
**Azure Database for PostgreSQL Flexible Server** + **Azure Blob Storage** +
**Azure OpenAI / Foundry** + **Application Insights**, all provisioned by
`infra/main.bicep`.

If you only need a working public URL with zero cost, see
[§ 6 — Lower-cost alternatives](#6--lower-cost-alternatives).

---

## 1 — Prerequisites

| Tool | Why | Install |
|---|---|---|
| Azure CLI ≥ 2.60 | provisioning + image push | <https://aka.ms/installazurecli> |
| Bicep CLI ≥ 0.30 | infra template language | `az bicep install` |
| Docker ≥ 24 | build the backend image | <https://docs.docker.com/get-docker/> |
| Node.js ≥ 20 | build the frontend bundle | <https://nodejs.org> |
| Python ≥ 3.13 | run migrations locally if needed | <https://www.python.org/downloads/> |

You also need an Azure subscription with quota for:
* Container Apps (1 environment, 1 app)
* Postgres Flexible Server (B1ms or larger)
* Storage Account (Standard LRS)
* Cognitive Services / Azure OpenAI (the `gpt-4o-mini` deployment)
* Optional: Cosmos DB (Serverless), Static Web Apps

## 2 — One-time secrets

Generate the secrets that aren't issued by Azure:

```powershell
# JWT signing secret
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Webhook HMAC secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Bootstrap admin password (any strong password)
```

Copy `.env.production.example` to `.env.production` and fill every value.
**Do not commit the filled copy** — it is in `.gitignore`.

## 3 — Provision Azure resources

```powershell
# Login + select subscription
az login
az account set --subscription "<SUBSCRIPTION_ID>"

# Provision everything in one go (resource group + workload module)
az deployment sub create `
  --location southeastasia `
  --template-file infra/main.bicep `
  --parameters `
    rgName=rg-sjplanner-prod `
    pgPassword="<POSTGRES_ADMIN_PASSWORD>" `
    backendImage="ghcr.io/<your-org>/sjplanner-api:latest"
```

The deployment outputs:
* `backendUrl` — public Container App FQDN
* `postgresHost` — DB host for `DATABASE_URL`
* `appInsightsConnection` — for `APPLICATIONINSIGHTS_CONNECTION_STRING`

## 4 — Database migrations

The backend Docker image runs `alembic upgrade head` on container start, so
the very first deployment creates every table. To run migrations manually
(e.g. before swapping the image):

```powershell
$env:DATABASE_URL = "<your prod DATABASE_URL>"
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current   # should print revision (head)
```

After model changes, generate a new revision:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

## 5 — CI/CD with GitHub Actions

Two workflows are pre-wired in `.github/workflows/`:

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | every push & PR | pytest (39 cases, offline) + frontend `tsc -b` + `vite build` |
| `deploy-azure.yml` | push to `main` (paths) **or** manual dispatch | buildx → GHCR → Azure OIDC login → Bicep `arm-deploy` → Container App image swap → `/api/health` smoke check |

### Required GitHub repo secrets

| Secret | Source |
|---|---|
| `AZURE_CLIENT_ID` | App registration with federated credential for the repo |
| `AZURE_TENANT_ID` | Entra tenant id |
| `AZURE_SUBSCRIPTION_ID` | Subscription id |
| `PG_PASSWORD` | Postgres admin password |

Configure the federated credential against `repo:<org>/<repo>:ref:refs/heads/main`.
See <https://learn.microsoft.com/azure/active-directory/develop/workload-identity-federation>.

### Container App env vars

After the first `arm-deploy`, set the rest of the values from
`.env.production` on the Container App:

```powershell
az containerapp update `
  --name sj-planner-api `
  --resource-group rg-sjplanner-prod `
  --set-env-vars `
    APP_ENV=production `
    LOG_JSON=true `
    JWT_SECRET=secretref:jwt-secret `
    AZURE_OPENAI_ENDPOINT=... `
    AZURE_OPENAI_API_KEY=secretref:aoai-key `
    AZURE_STORAGE_CONNECTION_STRING=secretref:blob-conn `
    APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:appi-conn
```

Use `secretref:` for anything sensitive — the underlying Container App secret
is created with `az containerapp secret set`.

## 6 — Lower-cost alternatives

| Stack | Cost | Caveats |
|---|---|---|
| **Render (backend) + Neon (Postgres) + Vercel (frontend)** | $0 forever-free tier | Render free tier sleeps after 15 min idle; cold start ~30 s |
| **Azure for Students** | $100 credit / 12 mo | Same flow as § 3, just smaller SKUs |
| **Hugging Face Spaces (Docker) + Neon + Vercel** | $0 | No native Bicep deploy; use the Dockerfile directly |
| **Self-host on a VM (Oracle Cloud free tier)** | $0 forever | Manual TLS + reverse-proxy setup |

For Render: point the service at `backend/Dockerfile`, set `DATABASE_URL` to
the Neon connection string, and add every `.env.production` value. The image
already runs `alembic upgrade head` before launching uvicorn, so no extra
release command is needed.

## 7 — Smoke check after deploy

```bash
curl -s https://<backend-fqdn>/api/health | jq
# expect: {"status":"ok","llm_enabled":true,"blob_storage_enabled":true,...}
```

Then login and pull the dashboard:

```bash
TOKEN=$(curl -s -X POST https://<backend-fqdn>/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"admin@sj-planner.local","password":"<bootstrap_password>"}' \
  | jq -r .access_token)

curl -s https://<backend-fqdn>/api/projects -H "authorization: Bearer $TOKEN" | jq length
```

If both return 200 with sensible bodies, the deployment is live.
