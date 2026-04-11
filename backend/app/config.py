from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ----- Azure OpenAI / Foundry -----
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-08-01-preview"

    # ----- Azure AI Search -----
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index: str = "sj-planner-notes"

    # ----- Azure Blob Storage (note attachments) -----
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "sj-planner-attachments"

    # ----- Azure Cosmos DB (optional event mirror) -----
    cosmos_connection_string: str = ""
    cosmos_database: str = "sj-planner"
    cosmos_container: str = "events"

    # ----- Database -----
    database_url: str = "sqlite:///./sj_planner.db"

    # ----- App -----
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    log_level: str = "INFO"
    log_json: bool = False

    # ----- Auth -----
    jwt_secret: str = "dev-only-change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 8
    # Microsoft Entra ID (Azure AD) — leave blank to disable
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_audience: str = ""  # API App ID URI

    # ----- Observability -----
    applicationinsights_connection_string: str = ""

    # ----- PII redaction -----
    redact_pii: bool = True

    # ----- Outbound webhooks (Power Automate) -----
    webhook_url_draft_created: str = ""
    webhook_url_draft_approved: str = ""
    webhook_signing_secret: str = ""

    # ----- Bootstrap admin (only used if DB has no users) -----
    bootstrap_admin_email: str = "admin" + "@" + "sj-planner.local"
    bootstrap_admin_password: str = "ChangeMe!123"
    bootstrap_org_name: str = "SJ Demo Organisation"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def search_enabled(self) -> bool:
        return bool(self.azure_search_endpoint and self.azure_search_api_key)

    @property
    def entra_enabled(self) -> bool:
        return bool(self.entra_tenant_id and self.entra_client_id)

    @property
    def appinsights_enabled(self) -> bool:
        return bool(self.applicationinsights_connection_string)

    @property
    def blob_storage_enabled(self) -> bool:
        return bool(self.azure_storage_connection_string and self.azure_storage_container)

    @property
    def cosmos_enabled(self) -> bool:
        return bool(self.cosmos_connection_string and self.cosmos_database and self.cosmos_container)

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
