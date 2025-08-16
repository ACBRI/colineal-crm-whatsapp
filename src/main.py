# src/main.py
import os
import google.generativeai as genai
from fastapi import FastAPI
from dotenv import load_dotenv

# 1. Cargar las variables de entorno ANTES que cualquier otra cosa.
load_dotenv()

# 2. Ahora que las variables existen, importar los módulos que las necesitan.
from .api.whatsapp_webhook import router as whatsapp_router

# Configuración de la API de Google (ahora sí encontrará la variable)
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    raise RuntimeError("La variable de entorno GOOGLE_API_KEY no está configurada.")

# Creación de la app FastAPI
app = FastAPI(
    title="Colineal CRM WhatsApp API",
    description="API para procesar mensajes de WhatsApp con IA y Odoo.",
    version="1.0.0"
)

# Incluir el router del webhook
app.include_router(whatsapp_router, prefix="/api", tags=["Webhooks"])

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "ok", "message": "API de Colineal funcionando"}