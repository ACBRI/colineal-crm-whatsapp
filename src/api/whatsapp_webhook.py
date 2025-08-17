# src/api/whatsapp_webhook.py (VERSIÓN OPTIMIZADA FINAL)
import os
import json
import google.generativeai as genai
from fastapi import APIRouter, Request, Response, HTTPException, Header
from typing import Optional, Dict, Any, List
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
    """
    try:
        print(f"📤 Enviando mensaje {context} a {phone_number}: {message[:50]}...")
        twilio_service.send_whatsapp_message(phone_number, message)
        print(f"✅ Mensaje {context} enviado exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error enviando mensaje {context} a {phone_number}: {e}")
        return False

@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request, x_twilio_signature: Optional[str] = Header(None)):
    """
    Webhook optimizado con conversación natural completa y lógica profesional de leads.
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
        conversation_history = conversation_context.get("history", [])
        
        print(f"📊 Contexto: Etapa={conversation_context['conversation_stage']}, Mensajes={conversation_context['message_count']}")
        
        # 2. Analizar mensaje con el clasificador inteligente mejorado
        analysis = ai_classifier.analyze_message_completeness(
            user_message=mensaje_cliente,
            conversation_history=conversation_history
        )
        
        # Extraer datos de análisis de forma segura
        analysis_data = analysis.get('analysis', {})
        quality = analysis_data.get('quality_assessment', 'cold')
        action = analysis.get('recommended_action', 'continue_conversation')
        final_action = analysis.get('final_action', action)
        
        print(f"🤖 Análisis IA: {action} → {final_action}, Calidad: {quality}")
        
        # 3. Agregar mensaje del usuario al historial
        conversation_service.add_message_to_conversation(
            phone_number=phone_number,
            message=mensaje_cliente,
            message_type="user",
            analysis=analysis 
        )
        
        # 4. Marcar mensaje como procesado
        redis_service.mark_message_as_processed(wamid)
        
        # 5. Procesar con lógica profesional optimizada
        response_data = await _process_intelligent_response_optimized(
            phone_number=phone_number,
            analysis=analysis,
            mensaje_cliente=mensaje_cliente,
            conversation_history=conversation_history
        )
        
        return response_data

    except json.JSONDecodeError as e:
        print(f"❌ Error JSON: {e}")
        # Respuesta de emergencia
        emergency_response = "Disculpa, tengo un problema técnico. Un asesor te contactará pronto."
        _safe_send_whatsapp_message(phone_number, emergency_response, "emergency")
        raise HTTPException(status_code=500, detail="La respuesta de la IA no es un JSON válido.")
        
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        # Respuesta de emergencia
        emergency_response = "Disculpa, tengo un problema técnico. Un asesor te contactará pronto."
        _safe_send_whatsapp_message(phone_number, emergency_response, "emergency")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

async def _process_intelligent_response_optimized(
    phone_number: str,
    analysis: Dict[str, Any],
    mensaje_cliente: str,
    conversation_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Procesa respuesta con lógica profesional y conversación natural.
    """
    
    # Obtener acción final y respuesta natural
    final_action = analysis.get("final_action", analysis.get("recommended_action", "continue_conversation"))
    natural_response = analysis.get("natural_response", analysis.get("suggested_reply", ""))
    
    print(f"🎯 Acción final: {final_action}")
    
    # SIEMPRE enviar respuesta natural primero
    if natural_response:
        message_sent = _safe_send_whatsapp_message(phone_number, natural_response, "natural_response")
        
        # Agregar respuesta al historial
        conversation_service.add_message_to_conversation(
            phone_number=phone_number,
            message=natural_response,
            message_type="assistant",
            analysis={"action": final_action, "response_type": "natural"}
        )
    else:
        message_sent = False
        print("⚠️ No se generó respuesta natural")
    
    # Procesar según acción determinada
    if final_action == "transfer_to_helpdesk" or analysis.get("is_support_request", False):
        return await _handle_support_transfer_optimized(phone_number, analysis, natural_response, message_sent)
    
    elif final_action == "create_lead_immediate" or ai_classifier.should_create_lead(analysis):
        return await _create_hot_lead_optimized(phone_number, analysis, mensaje_cliente, conversation_history, natural_response, message_sent)
    
    elif final_action == "nurture_and_qualify":
        return _handle_warm_lead_nurturing(phone_number, analysis, natural_response, message_sent)
    
    else:  # educate_and_build_interest o continue_conversation
        return _handle_cold_lead_education(phone_number, analysis, natural_response, message_sent)

async def _handle_support_transfer_optimized(
    phone_number: str, 
    analysis: Dict[str, Any], 
    natural_response: str, 
    message_sent: bool
) -> Dict[str, Any]:
    """Maneja transferencia a soporte con integración a Odoo Helpdesk."""
    
    print(f"🆘 Transferencia a soporte para {phone_number}")
    
    try:
        # Crear ticket en Odoo Helpdesk
        odoo_service = OdooService(
            url=settings.odoo_url,
            db=settings.odoo_db,
            username=settings.odoo_username,
            password=settings.odoo_password
        )
        
        extracted = analysis.get("extracted_data", {})
        analysis_data = analysis.get("analysis", {})
        
        # Datos del ticket de soporte
        ticket_data = {
            'name': f"Soporte WhatsApp - {phone_number}",
            'description': f"Consulta de soporte desde WhatsApp\n\nNecesidad: {extracted.get('intent', 'No especificada')}\nUrgencia: {extracted.get('urgency', 'medium')}\nRespuesta enviada: {natural_response}",
            'partner_phone': phone_number,
            'priority': '1' if extracted.get('urgency') == 'high' else '0',
            'x_source': 'WhatsApp'
        }
        
        # Intentar crear en helpdesk.ticket (si existe el módulo)
        try:
            ticket_id = odoo_service._get_connection().env['helpdesk.ticket'].create(ticket_data)
            print(f"✅ Ticket de soporte creado: {ticket_id}")
        except Exception as helpdesk_error:
            print(f"⚠️ Helpdesk no disponible: {helpdesk_error}")
            # Fallback: crear como lead de soporte
            ticket_data['name'] = f"[SOPORTE] {ticket_data['name']}"
            ticket_id = odoo_service._get_connection().env['crm.lead'].create(ticket_data)
            print(f"✅ Lead de soporte creado: {ticket_id}")
        
        return {
            "status": "support_transferred",
            "action": "transfer_to_helpdesk",
            "ticket_id": ticket_id,
            "message": natural_response,
            "message_sent": message_sent,
            "analysis": analysis
        }
        
    except Exception as e:
        print(f"❌ Error creando ticket de soporte: {e}")
        return {
            "status": "support_transfer_failed",
            "action": "transfer_to_helpdesk",
            "message": natural_response,
            "message_sent": message_sent,
            "error": str(e)
        }

async def _create_hot_lead_optimized(
    phone_number: str,
    analysis: Dict[str, Any],
    mensaje_cliente: str,
    conversation_history: List[Dict[str, Any]],
    natural_response: str,
    message_sent: bool
) -> Dict[str, Any]:
    """Crea lead HOT/calificado inmediatamente con datos enriquecidos."""
    
    quality = analysis.get("lead_quality", analysis.get("quality_assessment", "warm"))
    print(f"🔥 Creando lead {quality.upper()} para {phone_number}")
    
    try:
        odoo_service = OdooService(
            url=settings.odoo_url,
            db=settings.odoo_db,
            username=settings.odoo_username,
            password=settings.odoo_password
        )
        
        # Usar método profesional si está disponible, sino el estándar
        if hasattr(ai_classifier, 'format_lead_data_professional'):
            lead_data = ai_classifier.format_lead_data_professional(
                analysis, phone_number, conversation_history
            )
        else:
            lead_data = ai_classifier.format_lead_data(analysis, phone_number, mensaje_cliente)
        
        # Crear lead en Odoo
        lead_id = odoo_service.create_lead_from_whatsapp(
            phone_number=phone_number,
            message=mensaje_cliente,
            ai_analysis=analysis.get("analysis", analysis),
            lead_data=lead_data
        )
        
        # Marcar conversación como completada
        conversation_service.mark_lead_created(phone_number, lead_id)
        
        # Mensaje de confirmación adicional si es necesario
        if not natural_response or "contactará" not in natural_response.lower():
            confirmation_addition = "\n\n✅ He registrado tu información. Un especialista te contactará pronto."
            full_confirmation = (natural_response + confirmation_addition) if natural_response else confirmation_addition[3:]  # Quitar \n\n del inicio
            
            # Enviar confirmación adicional
            _safe_send_whatsapp_message(phone_number, confirmation_addition[3:], "lead_confirmation")
            
            # Agregar al historial
            conversation_service.add_message_to_conversation(
                phone_number=phone_number,
                message=confirmation_addition[3:],
                message_type="assistant",
                analysis={"action": "lead_confirmation", "lead_id": lead_id}
            )
        
        print(f"🎉 Lead {quality.upper()} {lead_id} creado exitosamente")
        
        return {
            "status": f"{quality}_lead_created",
            "action": "create_lead_immediate",
            "lead_id": lead_id,
            "lead_quality": quality,
            "message": natural_response,
            "message_sent": message_sent,
            "analysis": analysis
        }
        
    except Exception as e:
        print(f"❌ Error creando lead: {e}")
        
        # Respuesta de error
        error_message = "Hubo un problema técnico, pero hemos guardado tu información. Un asesor te contactará pronto."
        
        conversation_service.add_message_to_conversation(
            phone_number=phone_number,
            message=error_message,
            message_type="assistant",
            analysis={"action": "lead_creation_failed", "error": str(e)}
        )
        
        # Intentar enviar mensaje de error
        error_message_sent = _safe_send_whatsapp_message(phone_number, error_message, "error_response")
        
        return {
            "status": "lead_creation_failed",
            "action": "create_lead_immediate",
            "message": natural_response,
            "message_sent": message_sent,
            "error_message": error_message,
            "error_message_sent": error_message_sent,
            "error": str(e)
        }

def _handle_warm_lead_nurturing(
    phone_number: str,
    analysis: Dict[str, Any],
    natural_response: str,
    message_sent: bool
) -> Dict[str, Any]:
    """Maneja nurturing de leads WARM."""
    
    print(f"🟡 Nurturing WARM lead para {phone_number}")
    
    # Actualizar etapa de conversación
    conversation_service.add_message_to_conversation(
        phone_number=phone_number,
        message="[SISTEMA] Lead WARM en proceso de nurturing",
        message_type="system",
        analysis={
            "stage": "warm_nurturing", 
            "missing_info": analysis.get("missing_for_lead", []),
            "strategy": "continue_conversation_to_qualify"
        }
    )
    
    return {
        "status": "warm_lead_nurturing",
        "action": "nurture_and_qualify",
        "lead_quality": "warm",
        "message": natural_response,
        "message_sent": message_sent,
        "missing_info": analysis.get("missing_for_lead", []),
        "analysis": analysis,
        "next_steps": "continue_conversation"
    }

def _handle_cold_lead_education(
    phone_number: str,
    analysis: Dict[str, Any],
    natural_response: str,
    message_sent: bool
) -> Dict[str, Any]:
    """Maneja educación de leads COLD."""
    
    print(f"❄️ Educando COLD lead para {phone_number}")
    
    return {
        "status": "cold_lead_education",
        "action": "educate_and_build_interest",
        "lead_quality": "cold",
        "message": natural_response,
        "message_sent": message_sent,
        "needs_education": True,
        "analysis": analysis,
        "strategy": "build_interest_through_conversation"
    }

# FUNCIONES DE APOYO (mantenidas del código original)

def _generate_lead_confirmation_message(analysis: Dict[str, Any], lead_id: int) -> str:
    """Genera mensaje de confirmación personalizado como fallback."""
    
    # Intentar obtener datos de análisis de ambas estructuras posibles
    analysis_data = analysis.get("analysis", analysis)
    extracted_data = analysis_data.get("extracted_data", {})
    name = extracted_data.get("name")
    products = extracted_data.get("product_interest", [])
    
    if name and products:
        return f"¡Perfecto, {name}! He registrado tu interés en {', '.join(products)}. Un asesor especializado te contactará pronto. ¡Gracias por elegirnos! 🏠✨"
    elif name:
        return f"¡Excelente, {name}! He registrado tu consulta. Un asesor te contactará pronto. ¡Gracias por contactarnos! 😊"
    elif products:
        return f"¡Genial! He registrado tu interés en {', '.join(products)}. Un especialista se comunicará contigo pronto. ¡Gracias! 🛋️"
    else:
        return "¡Perfecto! He registrado tu consulta. Un asesor se comunicará contigo pronto. ¡Gracias por contactarnos! 📞"

# ================================
# ENDPOINTS ADICIONALES PARA GESTIÓN (sin cambios)
# ================================

@router.get("/conversation/{phone_number}/status")
async def get_conversation_status(phone_number: str):
    """Obtiene el estado actual de una conversación."""
    try:
        clean_phone = phone_number.replace("whatsapp:", "")
        summary = conversation_service.get_conversation_summary(clean_phone)
        return {"status": "success", "conversation": summary}
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
        conversation_key = f"conversation:{clean_phone}"
        completion_key = f"conversation_completed:{clean_phone}"
        redis_service.client.delete(conversation_key)
        redis_service.client.delete(completion_key)
        return {"status": "success", "message": f"Conversación de {clean_phone} reiniciada exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reiniciando conversación: {e}")

@router.get("/analytics/conversations")
async def get_conversation_analytics():
    """Obtiene analytics básicos de conversaciones."""
    try:
        all_keys = redis_service.client.keys("conversation:*")
        active_conversations = len([k for k in all_keys if not k.startswith("conversation_completed:")])
        completed_keys = redis_service.client.keys("conversation_completed:*")
        completed_conversations = len(completed_keys)
        total = active_conversations + completed_conversations
        return {
            "status": "success",
            "analytics": {
                "active_conversations": active_conversations,
                "completed_conversations": completed_conversations,
                "total_conversations": total,
                "completion_rate": round(completed_conversations / max(total, 1) * 100, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo analytics: {e}")

@router.get("/health")
async def health_check():
    """Endpoint de salud para monitoreo."""
    try:
        redis_status = "ok" if redis_service.client.ping() else "error"
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
            "services": {"redis": redis_status, "odoo": odoo_status, "ai": "ok"},
            "timestamp": json.dumps(datetime.now(), default=str)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en health check: {e}")