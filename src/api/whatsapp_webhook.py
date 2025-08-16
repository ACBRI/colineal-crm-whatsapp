# src/api/whatsapp_webhook.py
import os
import json
import google.generativeai as genai
from fastapi import APIRouter, Request, Response, HTTPException, Header
from typing import Optional

from ..services.redis_service import redis_service
from ..core.security import validate_twilio_signature
from ..services.odoo_service import OdooService
from ..config.settings import settings

# --- NUEVO PROMPT MEJORADO ---
SYSTEM_PROMPT = """Tu única función es analizar el texto de un usuario y devolver un único objeto JSON válido. No escribas absolutamente nada más que el objeto JSON. No incluyas explicaciones, saludos ni texto adicional. La salida debe ser exclusivamente el JSON.

La estructura del JSON debe ser la siguiente:
{"quality": "hot" | "warm" | "cold" | null, "intent": "string" | null, "entities": {"product_interest": ["string"], "location": "string"}, "is_support_request": true | false}

---
EJEMPLO 1:
USER_MESSAGE: "Hola, buenos días. Quería saber si tienen disponible el sofá modular gris que vi en su tienda de Quito. También, ¿cuál es el precio?"
JSON_OUTPUT: {"quality": "hot", "intent": "Solicitud de disponibilidad y precio de producto", "entities": {"product_interest": ["sofá modular gris"], "location": "Quito"}, "is_support_request": false}
---
EJEMPLO 2:
USER_MESSAGE: "Buenas, mi pedido no ha llegado y ya pasaron 5 días."
JSON_OUTPUT: {"quality": "cold", "intent": "Reclamo por retraso en la entrega de un pedido", "entities": {"product_interest": [], "location": null}, "is_support_request": true}
---

Ahora, procesa el siguiente mensaje del usuario.
"""

modelo_ia = genai.GenerativeModel('gemini-1.5-flash-latest')
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

router = APIRouter()

@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request, x_twilio_signature: Optional[str] = Header(None)):
    url = str(request.url)
    form_data = await request.form()
    data = dict(form_data)
    
    if not validate_twilio_signature(TWILIO_AUTH_TOKEN, x_twilio_signature, url, data):
        raise HTTPException(status_code=403, detail="Firma inválida. Acceso denegado.")

    wamid = data.get("SmsMessageSid")
    mensaje_cliente = data.get("Body")
    
    if not wamid or not mensaje_cliente:
        raise HTTPException(status_code=400, detail="Faltan datos esenciales (SmsMessageSid o Body).")

    if redis_service.is_message_processed(wamid):
        print(f"Mensaje duplicado recibido (wamid: {wamid}). Ignorando.")
        return Response(status_code=200, content="Mensaje duplicado, ignorado.")
    
    print(f"Mensaje nuevo recibido: {mensaje_cliente}")

    try:
        respuesta_ia = modelo_ia.generate_content([SYSTEM_PROMPT, mensaje_cliente])
        print(f"Respuesta de la IA: {respuesta_ia.text}")
        
        cleaned_text = respuesta_ia.text.strip().replace('```json', '').replace('```', '')
        json_response = json.loads(cleaned_text)

        redis_service.mark_message_as_processed(wamid)
        
        # NUEVO: Crear lead en Odoo automáticamente
        try:
            # Crear el servicio de Odoo
            odoo_service = OdooService(
                url=settings.odoo_url,
                db=settings.odoo_db, 
                username=settings.odoo_username,
                password=settings.odoo_password
            )
            
            # Obtener el número de teléfono
            phone_number = data.get("From", "Sin número")
            
            # Crear el lead en Odoo
            lead_id = odoo_service.create_lead_from_whatsapp(
                phone_number=phone_number,
                message=mensaje_cliente,
                ai_analysis=json_response
            )
            
            print(f"✅ Lead creado en Odoo con ID: {lead_id}")
            
            # Devolver respuesta exitosa
            return {
                "status": "success", 
                "analysis": json_response, 
                "lead_created": True,
                "lead_id": lead_id
            }
            
        except Exception as e:
            print(f"⚠️ Error creando lead en Odoo: {e}")
            # Si hay error con Odoo, devolver solo el análisis
            return {
                "status": "success", 
                "analysis": json_response, 
                "lead_created": False,
                "error": str(e)
            }

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="La respuesta de la IA no es un JSON válido.")
    except Exception as e:
        print(f"Error al procesar el mensaje: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")