# src/services/ai_classifier.py
import json
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIClassifier:
    """
    Clasificador inteligente que determina si hay información suficiente
    para crear un lead de calidad o si necesita más datos del usuario.
    """
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Criterios mínimos para crear un lead de calidad
        self.minimum_criteria = {
            "contact_info": ["name", "phone", "email"],  # Al menos uno
            "interest_level": ["product_interest", "specific_need"],  # Al menos uno
            "intent_clarity": ["clear_intent"]  # Debe estar presente
        }
    
    def analyze_message_completeness(self, user_message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Analiza si el mensaje contiene información suficiente para crear un lead
        o si necesita hacer preguntas de seguimiento.
        """
        
        prompt = self._build_completeness_prompt(user_message, conversation_history)
        
        try:
            response = self.model.generate_content([prompt, user_message])
            cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
            analysis = json.loads(cleaned_response)
            
            # Agregar recomendación de acción
            analysis["recommended_action"] = self._determine_action(analysis)
            analysis["next_question"] = self._generate_next_question(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis de completitud: {e}")
            return self._fallback_analysis()
    
    def _build_completeness_prompt(self, user_message: str, conversation_history: List[Dict] = None) -> str:
        """Construye el prompt para evaluar completitud de información."""
        
        return """ERES UN CLASIFICADOR DE LEADS INTELIGENTE. Tu función es analizar si hay información SUFICIENTE para crear un lead de calidad en el CRM.

DEVUELVE ÚNICAMENTE UN JSON VÁLIDO con esta estructura:
{
    "has_sufficient_info": true/false,
    "missing_info": ["campo1", "campo2"],
    "extracted_data": {
        "name": "string o null",
        "phone": "string o null", 
        "email": "string o null",
        "product_interest": ["array de productos"],
        "location": "string o null",
        "budget_range": "string o null",
        "urgency": "high/medium/low/null",
        "intent": "string"
    },
    "confidence_score": 0.0-1.0,
    "quality_assessment": "hot/warm/cold",
    "is_support_request": true/false,
    "conversation_stage": "initial/gathering_info/ready_for_lead/support"
}

CRITERIOS PARA has_sufficient_info = true:
✅ Tiene al menos UNA forma de contacto (nombre, teléfono confirmado, email)
✅ Tiene interés específico en productos/servicios
✅ Intención clara (compra, consulta, cotización)
✅ NO es solo un saludo genérico

CRITERIOS PARA has_sufficient_info = false:
❌ Solo saludo sin información específica ("Hola", "Buenos días")
❌ Pregunta muy vaga ("¿Qué venden?")
❌ Falta información de contacto básica
❌ No hay interés específico identificado

EJEMPLOS:

MENSAJE: "Hola, buenos días"
JSON: {"has_sufficient_info": false, "missing_info": ["contact_info", "product_interest", "specific_intent"], "extracted_data": {"name": null, "phone": null, "email": null, "product_interest": [], "location": null, "budget_range": null, "urgency": null, "intent": "saludo_inicial"}, "confidence_score": 0.2, "quality_assessment": "cold", "is_support_request": false, "conversation_stage": "initial"}

MENSAJE: "Hola, soy María. Quiero información sobre sofás modulares para mi sala. Mi presupuesto es de $2000"
JSON: {"has_sufficient_info": true, "missing_info": [], "extracted_data": {"name": "María", "phone": null, "email": null, "product_interest": ["sofás modulares"], "location": null, "budget_range": "$2000", "urgency": "medium", "intent": "solicitud_informacion_producto"}, "confidence_score": 0.8, "quality_assessment": "hot", "is_support_request": false, "conversation_stage": "ready_for_lead"}

MENSAJE: "Mi pedido no llegó aún"
JSON: {"has_sufficient_info": false, "missing_info": ["contact_info", "order_details"], "extracted_data": {"name": null, "phone": null, "email": null, "product_interest": [], "location": null, "budget_range": null, "urgency": "high", "intent": "reclamo_pedido"}, "confidence_score": 0.9, "quality_assessment": "cold", "is_support_request": true, "conversation_stage": "support"}

Analiza el siguiente mensaje:"""

    def _determine_action(self, analysis: Dict[str, Any]) -> str:
        """Determina la acción recomendada basada en el análisis."""
        
        if analysis.get("is_support_request", False):
            return "transfer_to_support"
        
        if analysis.get("has_sufficient_info", False):
            return "create_lead"
        
        confidence = analysis.get("confidence_score", 0)
        missing_info = analysis.get("missing_info", [])
        
        if confidence < 0.3:
            return "ask_clarifying_question"
        elif "contact_info" in missing_info:
            return "request_contact_info"
        elif "product_interest" in missing_info:
            return "ask_about_interest"
        else:
            return "gather_more_details"
    
    def _generate_next_question(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Genera la siguiente pregunta inteligente basada en el análisis."""
        
        action = analysis.get("recommended_action")
        missing_info = analysis.get("missing_info", [])
        conversation_stage = analysis.get("conversation_stage", "initial")
        
        questions = {
            "ask_clarifying_question": [
                "¡Hola! ¿En qué puedo ayudarte hoy?",
                "¿Hay algo específico que te interese de nuestros productos?",
                "¿Qué tipo de información necesitas?"
            ],
            
            "request_contact_info": [
                "Me encantaría ayudarte. ¿Podrías compartirme tu nombre para personalizar mejor la atención?",
                "Para enviarte información detallada, ¿me compartes tu nombre?",
                "¿Cómo te gusta que te llamen?"
            ],
            
            "ask_about_interest": [
                "¿Qué tipo de muebles te interesan específicamente?",
                "¿Para qué espacio de tu hogar estás buscando muebles?",
                "¿Hay algún estilo en particular que tengas en mente?"
            ],
            
            "gather_more_details": [
                "¿Tienes algún presupuesto en mente?",
                "¿En qué ciudad te encuentras?",
                "¿Es urgente o tienes tiempo para evaluar opciones?"
            ],
            
            "transfer_to_support": [
                "Entiendo tu consulta. Te voy a conectar con nuestro equipo de soporte para resolver tu situación."
            ]
        }
        
        if action in questions:
            # Rotar preguntas basado en el historial si es necesario
            return questions[action][0]  # Por ahora, primera pregunta
        
        return None
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """Análisis de respaldo en caso de error."""
        return {
            "has_sufficient_info": False,
            "missing_info": ["all_info"],
            "extracted_data": {},
            "confidence_score": 0.0,
            "quality_assessment": "cold",
            "is_support_request": False,
            "conversation_stage": "initial",
            "recommended_action": "ask_clarifying_question",
            "next_question": "¡Hola! ¿En qué puedo ayudarte hoy?"
        }
    
    def should_create_lead(self, analysis: Dict[str, Any]) -> bool:
        """Determina si se debe crear un lead basado en el análisis."""
        return (
            analysis.get("has_sufficient_info", False) and 
            not analysis.get("is_support_request", False) and
            analysis.get("confidence_score", 0) > 0.6
        )
    
    def format_lead_data(self, analysis: Dict[str, Any], phone_number: str, message: str) -> Dict[str, Any]:
        """Formatea los datos para crear un lead en Odoo."""
        
        extracted = analysis.get("extracted_data", {})
        
        # Construir descripción rica
        description_parts = [
            f"Mensaje original: {message}",
            f"Análisis IA: {analysis.get('intent', 'Sin análisis')}",
            f"Nivel de interés: {analysis.get('quality_assessment', 'N/A')}",
            f"Productos de interés: {', '.join(extracted.get('product_interest', []))}"
        ]
        
        if extracted.get("budget_range"):
            description_parts.append(f"Presupuesto: {extracted.get('budget_range')}")
        
        if extracted.get("urgency"):
            description_parts.append(f"Urgencia: {extracted.get('urgency')}")
        
        return {
            'name': self._generate_lead_name(extracted, phone_number),
            'phone': phone_number,
            'contact_name': extracted.get('name'),
            'email_from': extracted.get('email'),
            'city': extracted.get('location'),
            'description': '\n'.join(description_parts),
            'priority': self._map_urgency_to_priority(extracted.get('urgency')),
            # Campos personalizados si existen en Odoo
            'x_source': 'WhatsApp',
            'x_product_interest': ', '.join(extracted.get('product_interest', [])),
            'x_budget_range': extracted.get('budget_range'),
            'x_ai_confidence': analysis.get('confidence_score'),
            'x_quality_score': analysis.get('quality_assessment')
        }
    
    def _generate_lead_name(self, extracted_data: Dict, phone_number: str) -> str:
        """Genera un nombre descriptivo para el lead."""
        
        name = extracted_data.get('name')
        products = extracted_data.get('product_interest', [])
        
        if name and products:
            return f"{name} - {', '.join(products[:2])}"
        elif name:
            return f"{name} - Consulta WhatsApp"
        elif products:
            return f"Lead WhatsApp - {', '.join(products[:2])}"
        else:
            return f"Lead WhatsApp - {phone_number}"
    
    def _map_urgency_to_priority(self, urgency: str) -> str:
        """Mapea urgencia a prioridad de Odoo."""
        mapping = {
            "high": "3",      # Alta
            "medium": "2",    # Media  
            "low": "1",       # Baja
            None: "1"         # Por defecto
        }
        return mapping.get(urgency, "1")