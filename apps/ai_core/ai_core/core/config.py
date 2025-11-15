from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_token: str = "your-secure-api-token"
    # In a real application, you would add other configuration variables here.
    # For example:
    # database_url: str
    # allowed_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
