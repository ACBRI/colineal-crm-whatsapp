# src/main.py
import os
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

# 1. Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 2. Cargar las variables de entorno ANTES que cualquier otra cosa
load_dotenv()

# 3. Validar variables de entorno críticas
required_env_vars = [
    "GOOGLE_API_KEY",
    "TWILIO_AUTH_TOKEN", 
    "ODOO_URL",
    "ODOO_DB",
    "ODOO_USERNAME",
    "ODOO_PASSWORD"
]

missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    raise RuntimeError(f"Variables de entorno faltantes: {', '.join(missing_vars)}")

# 4. Configurar Google AI después de validar la variable
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    logger.info("✅ Google AI configurado exitosamente")
except Exception as e:
    raise RuntimeError(f"Error configurando Google AI: {e}")

# 5. Importar módulos después de configurar el entorno
from .api.whatsapp_webhook import router as whatsapp_router
from .services.redis_service import redis_service
from .services.conversation_service import conversation_service

# 6. Crear la aplicación FastAPI
app = FastAPI(
    title="Colineal CRM WhatsApp API - Fase 2",
    description="API inteligente para procesar mensajes de WhatsApp con IA y gestión conversacional en Odoo",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 7. Configurar CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 8. Incluir routers
app.include_router(whatsapp_router, prefix="/api", tags=["WhatsApp"])

# 9. Endpoints principales
@app.get("/", tags=["Root"])
def read_root():
    """Endpoint principal con información del sistema."""
    return {
        "status": "ok",
        "message": "Colineal CRM WhatsApp API - Fase 2",
        "version": "2.0.0",
        "features": [
            "Clasificador inteligente de leads",
            "Gestión conversacional",
            "Integración completa con Odoo",
            "Analytics de conversaciones",
            "Validación de mensajes duplicados"
        ]
    }

@app.get("/system/status", tags=["System"])
async def system_status():
    """Estado detallado del sistema."""
    
    try:
        # Verificar Redis
        redis_status = "connected" if redis_service.client.ping() else "disconnected"
        
        # Verificar servicios
        from .services.odoo_service import OdooService
        from .config.settings import settings
        
        try:
            odoo_service = OdooService(
                url=settings.odoo_url,
                db=settings.odoo_db,
                username=settings.odoo_username,
                password=settings.odoo_password
            )
            odoo_status = "connected" if odoo_service.test_connection() else "disconnected"
        except Exception as e:
            odoo_status = f"error: {str(e)}"
        
        # Estadísticas básicas
        try:
            all_conversations = redis_service.client.keys("conversation:*")
            completed_conversations = redis_service.client.keys("conversation_completed:*")
            
            stats = {
                "active_conversations": len(all_conversations),
                "completed_conversations": len(completed_conversations),
                "total_processed": len(all_conversations) + len(completed_conversations)
            }
        except Exception:
            stats = {"error": "No se pudieron obtener estadísticas"}
        
        return {
            "system_status": "operational",
            "services": {
                "redis": redis_status,
                "odoo": odoo_status,
                "google_ai": "operational",
                "webhook": "operational"
            },
            "conversation_stats": stats,
            "environment": {
                "python_version": os.sys.version,
                "fastapi_version": "0.116.1"
            }
        }
        
    except Exception as e:
        logger.error(f"Error en system status: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado del sistema: {e}")

@app.get("/system/config", tags=["System"])
def system_config():
    """Configuración del sistema (sin datos sensibles)."""
    
    return {
        "odoo_url": os.environ.get("ODOO_URL", "No configurado"),
        "odoo_db": os.environ.get("ODOO_DB", "No configurado"),
        "redis_configured": bool(os.environ.get("REDIS_URL")),
        "google_ai_configured": bool(os.environ.get("GOOGLE_API_KEY")),
        "twilio_configured": bool(os.environ.get("TWILIO_AUTH_TOKEN")),
        "environment": os.environ.get("ENVIRONMENT", "development")
    }

# 10. Manejo de eventos de inicio y cierre
@app.on_event("startup")
async def startup_event():
    """Tareas al iniciar la aplicación."""
    
    logger.info("🚀 Iniciando Colineal CRM WhatsApp API - Fase 2")
    
    try:
        # Verificar conexiones críticas
        if redis_service.client.ping():
            logger.info("✅ Redis conectado exitosamente")
        else:
            logger.warning("⚠️ Redis no disponible")
            
        # Verificar Odoo
        from .services.odoo_service import OdooService
        from .config.settings import settings
        
        odoo_service = OdooService(
            url=settings.odoo_url,
            db=settings.odoo_db,
            username=settings.odoo_username,
            password=settings.odoo_password
        )
        
        if odoo_service.test_connection():
            logger.info("✅ Odoo conectado exitosamente")
        else:
            logger.warning("⚠️ Odoo no disponible")
            
        logger.info("🎉 Sistema iniciado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante el inicio: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Tareas al cerrar la aplicación."""
    
    logger.info("🛑 Cerrando Colineal CRM WhatsApp API")
    
    try:
        # Cerrar conexiones si es necesario
        # Redis se cierra automáticamente
        logger.info("✅ Aplicación cerrada correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante el cierre: {e}")

# 11. Manejadores de errores globales
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Endpoint no encontrado",
        "message": "Verifica la URL y método HTTP",
        "available_endpoints": [
            "/docs - Documentación de la API",
            "/api/webhook/whatsapp - Webhook principal",
            "/system/status - Estado del sistema"
        ]
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Error interno del servidor: {exc}")
    return {
        "error": "Error interno del servidor",
        "message": "Contacta al administrador del sistema",
        "timestamp": str(datetime.now())
    }

# Importar datetime para manejo de errores
from datetime import datetime

# 12. Información adicional para desarrollo
if __name__ == "__main__":
    import uvicorn
    
    print("🔧 Ejecutando en modo desarrollo")
    print("📚 Documentación disponible en: http://127.0.0.1:8000/docs")
    print("🔍 Estado del sistema en: http://127.0.0.1:8000/system/status")
    
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )