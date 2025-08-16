import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Configuración de Odoo
    odoo_url: str
    odoo_db: str
    odoo_username: str
    odoo_password: str
    
    # Configuración existente
    google_api_key: str
    twilio_auth_token: str
    redis_url: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"

settings = Settings()