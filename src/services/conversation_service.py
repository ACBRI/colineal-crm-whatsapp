# src/services/conversation_service.py
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .redis_service import redis_service

logger = logging.getLogger(__name__)

class ConversationService:
    """
    Servicio que gestiona el estado de las conversaciones de WhatsApp
    y mantiene el historial para tomar decisiones inteligentes.
    """
    
    def __init__(self):
        self.redis = redis_service
        self.conversation_ttl = 86400 * 7  # 7 días
        self.max_messages_per_conversation = 50
    
    def get_conversation_history(self, phone_number: str) -> List[Dict[str, Any]]:
        """Obtiene el historial de conversación de un número de teléfono."""
        
        conversation_key = f"conversation:{phone_number}"
        
        try:
            history_json = self.redis.client.get(conversation_key)
            if history_json:
                return json.loads(history_json)
            return []
        except Exception as e:
            logger.error(f"Error obteniendo historial de {phone_number}: {e}")
            return []
    
    def add_message_to_conversation(
        self, 
        phone_number: str, 
        message: str, 
        message_type: str = "user",
        analysis: Dict[str, Any] = None
    ) -> None:
        """Agrega un mensaje al historial de conversación."""
        
        conversation_key = f"conversation:{phone_number}"
        
        try:
            # Obtener historial actual
            history = self.get_conversation_history(phone_number)
            
            # Crear nuevo mensaje
            new_message = {
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "type": message_type,  # "user" o "assistant"
                "analysis": analysis or {}
            }
            
            # Agregar al historial
            history.append(new_message)
            
            # Limitar tamaño del historial
            if len(history) > self.max_messages_per_conversation:
                history = history[-self.max_messages_per_conversation:]
            
            # Guardar en Redis
            self.redis.client.setex(
                conversation_key,
                self.conversation_ttl,
                json.dumps(history)
            )
            
        except Exception as e:
            logger.error(f"Error guardando mensaje de {phone_number}: {e}")
    
    def get_conversation_context(self, phone_number: str) -> Dict[str, Any]:
        """
        Obtiene el contexto completo de la conversación para tomar decisiones.
        """
        
        history = self.get_conversation_history(phone_number)
        
        if not history:
            return {
                "is_new_conversation": True,
                "message_count": 0,
                "last_interaction": None,
                "collected_data": {},
                "conversation_stage": "initial",
                "needs_follow_up": False
            }
        
        # Analizar el historial para extraer contexto
        collected_data = self._extract_collected_data(history)
        conversation_stage = self._determine_conversation_stage(history, collected_data)
        last_message = history[-1] if history else None
        
        return {
            "is_new_conversation": False,
            "message_count": len(history),
            "last_interaction": last_message.get("timestamp") if last_message else None,
            "collected_data": collected_data,
            "conversation_stage": conversation_stage,
            "needs_follow_up": self._needs_follow_up(history),
            "history": history[-5:]  # Últimos 5 mensajes para contexto
        }
    
    def _extract_collected_data(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extrae y consolida todos los datos recolectados en la conversación."""
        
        collected = {
            "name": None,
            "email": None,
            "product_interest": set(),
            "location": None,
            "budget_range": None,
            "urgency": None,
            "specific_needs": []
        }
        
        for message in history:
            analysis = message.get("analysis", {})
            extracted = analysis.get("extracted_data", {})
            
            # Consolidar información (último valor válido gana)
            if extracted.get("name"):
                collected["name"] = extracted["name"]
            
            if extracted.get("email"):
                collected["email"] = extracted["email"]
            
            if extracted.get("location"):
                collected["location"] = extracted["location"]
            
            if extracted.get("budget_range"):
                collected["budget_range"] = extracted["budget_range"]
            
            if extracted.get("urgency"):
                collected["urgency"] = extracted["urgency"]
            
            # Agregar productos de interés (acumular)
            if extracted.get("product_interest"):
                collected["product_interest"].update(extracted["product_interest"])
            
            # Agregar necesidades específicas
            if extracted.get("intent") and extracted["intent"] not in collected["specific_needs"]:
                collected["specific_needs"].append(extracted["intent"])
        
        # Convertir set a lista para JSON
        collected["product_interest"] = list(collected["product_interest"])
        
        return collected
    
    def _determine_conversation_stage(
        self, 
        history: List[Dict[str, Any]], 
        collected_data: Dict[str, Any]
    ) -> str:
        """Determina en qué etapa está la conversación."""
        
        if not history:
            return "initial"
        
        # Verificar si es una consulta de soporte
        last_analysis = history[-1].get("analysis", {})
        if last_analysis.get("is_support_request", False):
            return "support"
        
        # Verificar completitud de datos
        has_contact = collected_data.get("name") or collected_data.get("email")
        has_interest = len(collected_data.get("product_interest", [])) > 0
        has_clear_intent = len(collected_data.get("specific_needs", [])) > 0
        
        if has_contact and has_interest and has_clear_intent:
            return "ready_for_lead"
        elif has_interest or has_clear_intent:
            return "gathering_info"
        else:
            return "qualification"
    
    def _needs_follow_up(self, history: List[Dict[str, Any]]) -> bool:
        """Determina si la conversación necesita seguimiento."""
        
        if not history:
            return False
        
        last_message = history[-1]
        
        # Si el último mensaje fue del usuario y no se creó un lead, necesita seguimiento
        if last_message.get("type") == "user":
            last_analysis = last_message.get("analysis", {})
            return not last_analysis.get("has_sufficient_info", False)
        
        return False
    
    def mark_lead_created(self, phone_number: str, lead_id: int) -> None:
        """Marca en la conversación que se creó un lead."""
        
        try:
            # Obtener contexto actual
            context = self.get_conversation_context(phone_number)
            
            # Agregar mensaje del sistema sobre la creación del lead
            self.add_message_to_conversation(
                phone_number=phone_number,
                message=f"Lead creado exitosamente con ID: {lead_id}",
                message_type="system",
                analysis={"lead_created": True, "lead_id": lead_id}
            )
            
            # Marcar conversación como completada
            self._mark_conversation_completed(phone_number)
            
        except Exception as e:
            logger.error(f"Error marcando lead creado para {phone_number}: {e}")
    
    def _mark_conversation_completed(self, phone_number: str) -> None:
        """Marca una conversación como completada."""
        
        completion_key = f"conversation_completed:{phone_number}"
        self.redis.client.setex(completion_key, self.conversation_ttl, "completed")
    
    def is_conversation_completed(self, phone_number: str) -> bool:
        """Verifica si una conversación ya fue completada (lead creado)."""
        
        completion_key = f"conversation_completed:{phone_number}"
        return self.redis.client.exists(completion_key)
    
    def get_conversation_summary(self, phone_number: str) -> Dict[str, Any]:
        """Genera un resumen de la conversación para reportes."""
        
        context = self.get_conversation_context(phone_number)
        
        return {
            "phone_number": phone_number,
            "stage": context["conversation_stage"],
            "message_count": context["message_count"],
            "last_interaction": context["last_interaction"],
            "collected_data": context["collected_data"],
            "is_completed": self.is_conversation_completed(phone_number),
            "data_completeness": self._calculate_completeness(context["collected_data"])
        }
    
    def _calculate_completeness(self, collected_data: Dict[str, Any]) -> float:
        """Calcula el porcentaje de completitud de los datos."""
        
        required_fields = ["name", "product_interest", "specific_needs"]
        optional_fields = ["email", "location", "budget_range", "urgency"]
        
        required_score = sum(1 for field in required_fields if collected_data.get(field))
        optional_score = sum(1 for field in optional_fields if collected_data.get(field))
        
        total_score = (required_score / len(required_fields)) * 0.7 + (optional_score / len(optional_fields)) * 0.3
        
        return round(total_score, 2)

# Instancia del servicio
conversation_service = ConversationService()