# src/services/redis_service.py
import redis
import os

class RedisService:
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)

    def is_message_processed(self, wamid: str) -> bool:
        """Verifica si un ID de mensaje ya existe en Redis."""
        return self.client.exists(wamid)

    def mark_message_as_processed(self, wamid: str):
        """Marca un ID de mensaje como procesado con una expiración de 24 horas."""
        # El TTL (Time To Live) es importante para no llenar la memoria de Redis
        self.client.setex(wamid, 86400, "processed")

# Instancia única del servicio para ser usada en la app
redis_service = RedisService(os.environ.get("REDIS_URL"))