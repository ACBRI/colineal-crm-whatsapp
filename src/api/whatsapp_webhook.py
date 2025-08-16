# src/api/whatsapp_webhook.py
import os
import json
import google.generativeai as genai
from fastapi import APIRouter, Request, Response, HTTPException, Header
from typing import Optional, Dict, Any
from datetime import datetime

from ..services.redis_service import redis_service
from ..services.ai_classifier import AIClassifier
from ..services.conversation_service import conversation_service
from ..core.security import validate_twilio_signature
from ..services.odoo_service import OdooService
from ..config.settings import settings
from ..services.twilio_service import twilio_service


# Inicializar servicios
ai_classifier = AIClassifier()
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

router = APIRouter()

def _safe_send_whatsapp_message(phone_number: str, message: str, context: str = "") -> bool:
    """
    Envía un mensaje de WhatsApp de forma segura, manejando errores sin afectar el flujo principal.
    
    Args:
        phone_number: Número de teléfono del destinatario
        message: Mensaje a enviar
        context: Contexto para logging (ej: "follow_up", "lead_confirmation")
    
    Returns:
        bool: True si se envió exitosamente, False en caso de error
    """
    try:
        print(f"📤 Enviando mensaje {context} a {phone_number}: {message[:50]}...")
        twilio_service.send_whatsapp_message(phone_number, message)
        print(f"✅ Mensaje {context} enviado exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error enviando mensaje {context} a {phone_number}: {e}")
        # El error se loguea pero no interrumpe el flujo principal
        return False

@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request, x_twilio_signature: Optional[str] = Header(None)):
    """
    Webhook mejorado que usa el clasificador inteligente para determinar
    si crear un lead o hacer preguntas de seguimiento.
    """
    
    url = str(request.url)
    form_data = await request.form()
    data = dict(form_data)
    
    # Validar firma de Twilio
    if not validate_twilio_signature(TWILIO_AUTH_TOKEN, x_twilio_signature, url, data):
        raise HTTPException(status_code=403, detail="Firma inválida. Acceso denegado.")

    wamid = data.get("SmsMessageSid")
    mensaje_cliente = data.get("Body")
    phone_number = data.get("From", "Sin número")
    
    if not wamid or not mensaje_cliente:
        raise HTTPException(status_code=400, detail="Faltan datos esenciales (SmsMessageSid o Body).")

    # Verificar duplicados
    if redis_service.is_message_processed(wamid):
        print(f"Mensaje duplicado recibido (wamid: {wamid}). Ignorando.")
        return Response(status_code=200, content="Mensaje duplicado, ignorado.")
    
    print(f"📱 Nuevo mensaje de {phone_number}: {mensaje_cliente}")

    try:
        # 1. Obtener contexto de la conversación
        conversation_context = conversation_service.get_conversation_context(phone_number)
        print(f"📊 Contexto: Etapa={conversation_context['conversation_stage']}, Mensajes={conversation_context['message_count']}")
        
        # 2. Analizar mensaje con el clasificador inteligente
        analysis = ai_classifier.analyze_message_completeness(
            user_message=mensaje_cliente,
            conversation_history=conversation_context.get("history", [])
        )
        
        print(f"🤖 Análisis IA: {analysis['recommended_action']}, Confianza: {analysis['confidence_score']}")
        
        # 3. Agregar mensaje al historial
        conversation_service.add_message_to_conversation(
            phone_number=phone_number,
            message=mensaje_cliente,
            message_type="user",
            analysis=analysis
        )
        
        # 4. Marcar mensaje como procesado
        redis_service.mark_message_as_processed(wamid)
        
        # 5. Decidir acción basada en el análisis
        response_data = await _process_intelligent_response(
            phone_number=phone_number,
            analysis=analysis,
            mensaje_cliente=mensaje_cliente,
            conversation_context=conversation_context
        )
        
        return response_data

    except json.JSONDecodeError as e:
        print(f"❌ Error JSON: {e}")
        raise HTTPException(status_code=500, detail="La respuesta de la IA no es un JSON válido.")
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


async def _process_intelligent_response(
    phone_number: str,
    analysis: Dict[str, Any],
    mensaje_cliente: str,
    conversation_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Procesa la respuesta inteligente basada en el análisis del clasificador.
    """
    
    recommended_action = analysis.get("recommended_action")
    
    # Caso 1: Es una solicitud de soporte
    if recommended_action == "transfer_to_support":
        return _handle_support_request(phone_number, analysis)
    
    # Caso 2: Información suficiente para crear lead
    if ai_classifier.should_create_lead(analysis):
        return await _create_qualified_lead(phone_number, analysis, mensaje_cliente)
    
    # Caso 3: Necesita más información - generar pregunta de seguimiento
    return _generate_follow_up_question(phone_number, analysis)


def _handle_support_request(phone_number: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Maneja solicitudes de soporte."""
    
    print(f"🆘 Solicitud de soporte detectada para {phone_number}")
    
    # Agregar respuesta del asistente
    response_message = analysis.get("next_question", "Te conectaré con nuestro equipo de soporte.")
    
    conversation_service.add_message_to_conversation(
        phone_number=phone_number,
        message=response_message,
        message_type="assistant",
        analysis={"action": "support_transfer"}
    )
    
    # Enviar mensaje de WhatsApp
    message_sent = _safe_send_whatsapp_message(phone_number, response_message, "support_transfer")
    
    return {
        "status": "support_request",
        "action": "transfer_to_support",
        "message": response_message,
        "message_sent": message_sent,
        "analysis": analysis
    }


async def _create_qualified_lead(
    phone_number: str, 
    analysis: Dict[str, Any], 
    mensaje_cliente: str
) -> Dict[str, Any]:
    """Crea un lead cualificado en Odoo."""
    
    print(f"✅ Creando lead cualificado para {phone_number}")
    
    try:
        odoo_service = OdooService(
            url=settings.odoo_url,
            db=settings.odoo_db,
            username=settings.odoo_username,
            password=settings.odoo_password
        )
        
        # Formatear datos del lead usando el clasificador
        lead_data = ai_classifier.format_lead_data(analysis, phone_number, mensaje_cliente)
        
        # Crear lead en Odoo
        lead_id = odoo_service.create_lead_from_whatsapp(
            phone_number=phone_number,
            message=mensaje_cliente,
            ai_analysis=analysis,
            lead_data=lead_data
        )
        
        # Marcar conversación como completada
        conversation_service.mark_lead_created(phone_number, lead_id)
        
        # Mensaje de confirmación al cliente
        confirmation_message = _generate_lead_confirmation_message(analysis, lead_id)
        
        conversation_service.add_message_to_conversation(
            phone_number=phone_number,
            message=confirmation_message,
            message_type="assistant",
            analysis={"action": "lead_created", "lead_id": lead_id}
        )
        
        # Enviar mensaje de confirmación por WhatsApp
        message_sent = _safe_send_whatsapp_message(phone_number, confirmation_message, "lead_confirmation")
        
        print(f"🎉 Lead {lead_id} creado exitosamente")
        
        return {
            "status": "success",
            "action": "lead_created",
            "lead_id": lead_id,
            "analysis": analysis,
            "message": confirmation_message,
            "message_sent": message_sent,
            "lead_created": True
        }
        
    except Exception as e:
        print(f"❌ Error creando lead: {e}")
        
        # Respuesta de error pero continuamos la conversación
        error_message = "Hubo un problema técnico, pero hemos guardado tu información. Un asesor te contactará pronto."
        
        conversation_service.add_message_to_conversation(
            phone_number=phone_number,
            message=error_message,
            message_type="assistant",
            analysis={"action": "lead_creation_failed", "error": str(e)}
        )
        
        # Intentar enviar mensaje de error (no crítico si falla)
        message_sent = _safe_send_whatsapp_message(phone_number, error_message, "error_response")
        
        return {
            "status": "error",
            "action": "lead_creation_failed",
            "analysis": analysis,
            "message": error_message,
            "message_sent": message_sent,
            "lead_created": False,
            "error": str(e)
        }


def _generate_follow_up_question(phone_number: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Genera pregunta de seguimiento inteligente."""
    
    next_question = analysis.get("next_question")
    recommended_action = analysis.get("recommended_action")
    
    print(f"❓ Generando pregunta de seguimiento para {phone_number}: {recommended_action}")
    
    if not next_question:
        next_question = "¿En qué más puedo ayudarte?"
    
    # Agregar respuesta del asistente al historial
    conversation_service.add_message_to_conversation(
        phone_number=phone_number,
        message=next_question,
        message_type="assistant",
        analysis={"action": recommended_action}
    )
    
    # Enviar pregunta de seguimiento por WhatsApp
    message_sent = _safe_send_whatsapp_message(phone_number, next_question, "follow_up")
    
    return {
        "status": "gathering_info",
        "action": recommended_action,
        "message": next_question,
        "message_sent": message_sent,
        "analysis": analysis,
        "lead_created": False,
        "needs_more_info": True
    }


def _generate_lead_confirmation_message(analysis: Dict[str, Any], lead_id: int) -> str:
    """Genera mensaje de confirmación personalizado cuando se crea un lead."""
    
    extracted_data = analysis.get("extracted_data", {})
    name = extracted_data.get("name")
    products = extracted_data.get("product_interest", [])
    
    # Personalizar mensaje según la información disponible
    if name and products:
        return f"¡Perfecto, {name}! He registrado tu interés en {', '.join(products)}. Un asesor especializado te contactará pronto para ayudarte con toda la información que necesitas. ¡Gracias por elegirnos! 🏠✨"
    elif name:
        return f"¡Excelente, {name}! He registrado tu consulta y un asesor te contactará pronto para brindarte la mejor atención personalizada. ¡Gracias por contactarnos! 😊"
    elif products:
        return f"¡Genial! He registrado tu interés en {', '.join(products)}. Un especialista de nuestro equipo se comunicará contigo pronto para ayudarte con toda la información que necesitas. ¡Gracias! 🛋️"
    else:
        return "¡Perfecto! He registrado tu consulta y un asesor de nuestro equipo se comunicará contigo pronto para brindarte la mejor atención. ¡Gracias por contactarnos! 📞"


# ================================
# ENDPOINTS ADICIONALES PARA GESTIÓN
# ================================

@router.get("/conversation/{phone_number}/status")
async def get_conversation_status(phone_number: str):
    """Obtiene el estado actual de una conversación."""
    
    try:
        # Limpiar número de teléfono (quitar prefijos de WhatsApp)
        clean_phone = phone_number.replace("whatsapp:", "")
        
        summary = conversation_service.get_conversation_summary(clean_phone)
        
        return {
            "status": "success",
            "conversation": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {e}")


@router.get("/conversation/{phone_number}/history")
async def get_conversation_history(phone_number: str):
    """Obtiene el historial completo de una conversación."""
    
    try:
        clean_phone = phone_number.replace("whatsapp:", "")
        history = conversation_service.get_conversation_history(clean_phone)
        
        return {
            "status": "success",
            "phone_number": clean_phone,
            "message_count": len(history),
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {e}")


@router.post("/conversation/{phone_number}/reset")
async def reset_conversation(phone_number: str):
    """Reinicia una conversación (para testing o casos especiales)."""
    
    try:
        clean_phone = phone_number.replace("whatsapp:", "")
        
        # Eliminar historial de conversación
        conversation_key = f"conversation:{clean_phone}"
        completion_key = f"conversation_completed:{clean_phone}"
        
        redis_service.client.delete(conversation_key)
        redis_service.client.delete(completion_key)
        
        return {
            "status": "success",
            "message": f"Conversación de {clean_phone} reiniciada exitosamente"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reiniciando conversación: {e}")


@router.get("/analytics/conversations")
async def get_conversation_analytics():
    """Obtiene analytics básicos de conversaciones."""
    
    try:
        # Esta es una implementación básica - se puede expandir
        all_keys = redis_service.client.keys("conversation:*")
        active_conversations = len([k for k in all_keys if not k.startswith("conversation_completed:")])
        
        completed_keys = redis_service.client.keys("conversation_completed:*")
        completed_conversations = len(completed_keys)
        
        return {
            "status": "success",
            "analytics": {
                "active_conversations": active_conversations,
                "completed_conversations": completed_conversations,
                "total_conversations": active_conversations + completed_conversations,
                "completion_rate": round(completed_conversations / max(active_conversations + completed_conversations, 1) * 100, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo analytics: {e}")


@router.get("/health")
async def health_check():
    """Endpoint de salud para monitoreo."""
    
    try:
        # Verificar Redis
        redis_status = "ok" if redis_service.client.ping() else "error"
        
        # Verificar Odoo (conexión básica)
        try:
            odoo_service = OdooService(
                url=settings.odoo_url,
                db=settings.odoo_db,
                username=settings.odoo_username,
                password=settings.odoo_password
            )
            odoo_status = "ok" if odoo_service.test_connection() else "error"
        except:
            odoo_status = "error"
        
        return {
            "status": "healthy",
            "services": {
                "redis": redis_status,
                "odoo": odoo_status,
                "ai": "ok"  # Si llegamos aquí, FastAPI está funcionando
            },
            "timestamp": json.dumps(datetime.now(), default=str)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en health check: {e}")