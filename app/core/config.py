from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PGSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres"
    DB_NAME: str = "postgres"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    BUILDINGS_BUCKET: str = "buildings"
    INFERENCE_BUCKET: str = "inference"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()