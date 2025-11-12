from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gcp_project_id: str | None = None
    gcp_location: str = "us-central1"
    vertex_model_name: str = "gemini-1.5-pro"
    google_application_credentials: str | None = None
    max_pdf_chunk_size: int = 1500
    pdf_chunk_overlap: int = 200

    @property
    def project_path(self) -> str | None:
        return self.google_application_credentials


settings = Settings()

