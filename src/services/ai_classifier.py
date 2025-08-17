# src/services/ai_classifier.py (VERSIÓN BÁSICA - SOLO CAMPOS GARANTIZADOS)
import json
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AIClassifier:
    """
    Clasificador inteligente con conversación natural y lógica profesional.
    Compatible con Odoo básico (sin campos personalizados).
    """
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Criterios mínimos para crear un lead de calidad
        self.minimum_criteria = {
            "contact_info": ["name", "phone", "email"],  # Al menos uno
            "interest_level": ["product_interest", "specific_need"],  # Al menos uno
            "intent_clarity": ["clear_intent"]  # Debe estar presente
        }
        
        # Estrategias por calidad de lead
        self.lead_strategies = {
            "hot": {"min_confidence": 0.7, "should_create_lead": True},
            "warm": {"min_confidence": 0.5, "should_create_lead": False},
            "cold": {"min_confidence": 0.3, "should_create_lead": False}
        }
    
    def analyze_message_completeness(self, user_message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Analiza el mensaje del usuario y genera respuesta conversacional natural
        con lógica profesional de leads.
        """
        
        prompt = self._build_conversational_prompt(user_message, conversation_history)
        
        try:
            response = self.model.generate_content([prompt, user_message])
            cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
            analysis = json.loads(cleaned_response)
            
            # AGREGAR COMPATIBILIDAD con webhook existente
            analysis = self._ensure_compatibility(analysis)
            
            # AGREGAR LÓGICA PROFESIONAL
            analysis = self._add_professional_logic(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis conversacional: {e}")
            return self._fallback_analysis()
    
    def _build_conversational_prompt(self, user_message: str, conversation_history: List[Dict] = None) -> str:
        """Prompt optimizado para conversación natural."""
        
        history_str = json.dumps(conversation_history[-5:], indent=2) if conversation_history else "[]"

        return f"""ERES UN ASISTENTE DE VENTAS CONVERSACIONAL EXPERTO para COLINEAL, una tienda de muebles y decoración.

REGLAS DE CONVERSACIÓN:
✅ Responde DIRECTAMENTE las preguntas del usuario PRIMERO
✅ Usa lenguaje claro y simple
✅ Oraciones cortas e impactantes
✅ Voz activa, nunca pasiva
✅ Usa "tú" y "tu" para dirigirte al usuario
✅ Sé natural, útil y profesional

PALABRAS PROHIBIDAS (NUNCA usar):
❌ puede, podría, solo, que, muy, realmente, literalmente, actualmente, ciertamente, probablemente, básicamente, tal vez, profundizar, embarcarse, estimado, crear, creando, imaginar, reino, revolucionario, desbloquear, descubrir, utilizar, utilizando, sumergirse, revelar, fundamental, elucidar, por lo tanto, además, sin embargo, aprovechar, emocionante, innovador, poderoso, consultas

FORMATO PROHIBIDO:
❌ NO uses guiones largos, punto y coma, hashtags, markdown, asteriscos
❌ NO seas robótico ni repetitivo
❌ NO ignores las preguntas del usuario

PRODUCTOS COLINEAL:
• Sofás y muebles para sala
• Comedores y mesas  
• Muebles para dormitorio
• Decoración y textiles (manteles, cojines, cortinas)
• Muebles de oficina
• Accesorios decorativos

LÓGICA DE CALIFICACIÓN:
🔥 HOT: Tiene nombre + producto específico + presupuesto/urgencia
🟡 WARM: Tiene algún dato útil + interés específico
❄️ COLD: Solo saludo o pregunta general
🆘 SOPORTE: Problemas, reclamos, post-venta

ESTRUCTURA JSON (responder ÚNICAMENTE con esto):
{{
    "analysis": {{
        "has_sufficient_info": true/false,
        "missing_info": ["campo1", "campo2"],
        "extracted_data": {{
            "name": "string o null",
            "phone": "string o null",
            "email": "string o null",
            "product_interest": ["array de productos"],
            "location": "string o null",
            "budget_range": "string o null",
            "urgency": "high/medium/low/null",
            "intent": "string"
        }},
        "confidence_score": 0.0-1.0,
        "quality_assessment": "hot/warm/cold",
        "is_support_request": true/false,
        "conversation_stage": "initial/gathering_info/ready_for_lead/support"
    }},
    "suggested_reply": "Respuesta natural y directa que contesta la pregunta del usuario",
    "recommended_action": "create_lead/continue_conversation/transfer_to_support"
}}

EJEMPLOS:

USUARIO: "¿Qué venden?"
RESPUESTA: {{
    "analysis": {{
        "has_sufficient_info": false,
        "missing_info": ["contact_info", "specific_product"],
        "extracted_data": {{"name": null, "phone": null, "email": null, "product_interest": [], "location": null, "budget_range": null, "urgency": null, "intent": "información_general"}},
        "confidence_score": 0.3,
        "quality_assessment": "cold",
        "is_support_request": false,
        "conversation_stage": "initial"
    }},
    "suggested_reply": "¡Hola! Somos COLINEAL, especialistas en muebles y decoración para tu hogar. Tenemos sofás, comedores, muebles de dormitorio y accesorios decorativos. ¿Hay algo específico que buscas para tu casa?",
    "recommended_action": "continue_conversation"
}}

USUARIO: "Soy María, busco un sofá de 3 puestos, tengo $2000"
RESPUESTA: {{
    "analysis": {{
        "has_sufficient_info": true,
        "missing_info": [],
        "extracted_data": {{"name": "María", "phone": null, "email": null, "product_interest": ["sofá 3 puestos"], "location": null, "budget_range": "$2000", "urgency": "medium", "intent": "compra_sofá"}},
        "confidence_score": 0.9,
        "quality_assessment": "hot",
        "is_support_request": false,
        "conversation_stage": "ready_for_lead"
    }},
    "suggested_reply": "¡Perfecto, María! Tenemos excelentes opciones de sofás de 3 puestos en tu presupuesto. ¿Prefieres algún estilo en particular? ¿Moderno, clásico o algo específico?",
    "recommended_action": "create_lead"
}}

HISTORIAL: {history_str}

MENSAJE A ANALIZAR:"""

    def _ensure_compatibility(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Asegura compatibilidad con el webhook existente."""
        
        # Asegurar que recommended_action existe
        if "recommended_action" not in analysis:
            analysis["recommended_action"] = self._determine_action(analysis.get("analysis", {}))
        
        # Crear campos adicionales para compatibilidad
        analysis_data = analysis.get("analysis", {})
        
        # Campos que espera el webhook
        analysis["has_sufficient_info"] = analysis_data.get("has_sufficient_info", False)
        analysis["extracted_data"] = analysis_data.get("extracted_data", {})
        analysis["confidence_score"] = analysis_data.get("confidence_score", 0.0)
        analysis["quality_assessment"] = analysis_data.get("quality_assessment", "cold")
        analysis["is_support_request"] = analysis_data.get("is_support_request", False)
        analysis["conversation_stage"] = analysis_data.get("conversation_stage", "initial")
        
        # Crear next_question desde suggested_reply
        analysis["next_question"] = analysis.get("suggested_reply", "¿En qué puedo ayudarte?")
        analysis["natural_response"] = analysis.get("suggested_reply", "¿En qué puedo ayudarte?")
        
        return analysis
    
    def _add_professional_logic(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Agrega lógica profesional para manejo de leads."""
        
        quality = analysis.get("quality_assessment", "cold")
        confidence = analysis.get("confidence_score", 0)
        
        # Determinar acción final
        if analysis.get("is_support_request", False):
            analysis["final_action"] = "transfer_to_helpdesk"
        elif quality == "hot" and confidence >= 0.7 and analysis.get("has_sufficient_info", False):
            analysis["final_action"] = "create_lead_immediate"
        elif quality == "warm" and confidence >= 0.5:
            analysis["final_action"] = "nurture_and_qualify"
        else:
            analysis["final_action"] = "educate_and_build_interest"
        
        # Campos adicionales
        analysis["lead_quality"] = quality
        analysis["missing_for_lead"] = self._calculate_missing_info(analysis)
        
        return analysis
    
    def _calculate_missing_info(self, analysis: Dict[str, Any]) -> List[str]:
        """Calcula información faltante para crear lead."""
        
        extracted = analysis.get("extracted_data", {})
        missing = []
        
        if not extracted.get("name"):
            missing.append("contact_info")
        
        if not extracted.get("product_interest"):
            missing.append("specific_product")
        
        if not extracted.get("intent") or extracted.get("intent") == "información_general":
            missing.append("clear_intent")
        
        return missing
    
    def _determine_action(self, analysis: Dict[str, Any]) -> str:
        """Determina acción como fallback."""
        if analysis.get("is_support_request", False):
            return "transfer_to_support"
        if analysis.get("has_sufficient_info", False):
            return "create_lead"
        return "continue_conversation"
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """Análisis de respaldo mejorado."""
        return {
            "analysis": {
                "has_sufficient_info": False,
                "missing_info": ["all_info"],
                "extracted_data": {},
                "confidence_score": 0.1,
                "quality_assessment": "cold",
                "is_support_request": False,
                "conversation_stage": "initial"
            },
            "suggested_reply": "¡Hola! Soy el asistente de COLINEAL. ¿En qué puedo ayudarte hoy?",
            "recommended_action": "continue_conversation",
            "has_sufficient_info": False,
            "extracted_data": {},
            "confidence_score": 0.1,
            "quality_assessment": "cold",
            "is_support_request": False,
            "conversation_stage": "initial",
            "next_question": "¡Hola! Soy el asistente de COLINEAL. ¿En qué puedo ayudarte hoy?",
            "natural_response": "¡Hola! Soy el asistente de COLINEAL. ¿En qué puedo ayudarte hoy?",
            "final_action": "educate_and_build_interest",
            "lead_quality": "cold",
            "missing_for_lead": ["all_info"]
        }
    
    def should_create_lead(self, analysis: Dict[str, Any]) -> bool:
        """Determina si crear lead (mantiene compatibilidad)."""
        return (
            analysis.get("final_action") == "create_lead_immediate" or
            (analysis.get("recommended_action") == "create_lead" and
             analysis.get("has_sufficient_info", False) and
             not analysis.get("is_support_request", False))
        )
    
    def format_lead_data(self, analysis: Dict[str, Any], phone_number: str, message: str) -> Dict[str, Any]:
        """Formatea datos para crear lead (SOLO CAMPOS BÁSICOS)."""
        
        # Usar analysis directamente o analysis.analysis según estructura
        analysis_data = analysis.get("analysis", analysis)
        extracted = analysis_data.get("extracted_data", {})
        
        # Construir descripción rica con toda la información
        description_parts = [
            f"Mensaje original: {message}",
            f"Fuente: WhatsApp",
            f"Análisis IA: {extracted.get('intent', 'Sin análisis')}",
            f"Nivel de interés: {analysis_data.get('quality_assessment', 'N/A')}"
        ]
        
        # Agregar productos de interés a la descripción
        if extracted.get("product_interest"):
            description_parts.append(f"Productos de interés: {', '.join(extracted['product_interest'])}")
        
        # Agregar presupuesto a la descripción
        if extracted.get("budget_range"):
            description_parts.append(f"Presupuesto mencionado: {extracted.get('budget_range')}")
        
        # Agregar urgencia a la descripción
        if extracted.get("urgency"):
            description_parts.append(f"Urgencia: {extracted.get('urgency')}")
        
        # Agregar confianza del análisis
        if analysis_data.get('confidence_score'):
            description_parts.append(f"Confianza del análisis: {analysis_data.get('confidence_score'):.2f}")
        
        # SOLO USAR CAMPOS BÁSICOS DE ODOO
        return {
            'name': self._generate_lead_name(extracted, phone_number),
            'phone': phone_number,
            'contact_name': extracted.get('name'),
            'email_from': extracted.get('email'),
            'city': extracted.get('location'),
            'description': '\n'.join(description_parts),
            'priority': self._map_urgency_to_priority(extracted.get('urgency'))
            # ELIMINAMOS TODOS LOS CAMPOS x_ porque no existen en tu Odoo
        }
    
    def format_lead_data_professional(self, analysis: Dict[str, Any], phone_number: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Versión profesional usando SOLO campos básicos."""
        
        extracted = analysis.get("extracted_data", {})
        lead_quality = analysis.get("lead_quality", "warm")
        
        # Construir descripción profesional rica
        description_parts = [
            f"=== LEAD {lead_quality.upper()} DESDE WHATSAPP ===",
            f"Confianza del análisis: {analysis.get('confidence_score', 0):.2f}",
            f"Necesidad específica: {extracted.get('intent', 'No especificada')}",
            f"Fuente: WhatsApp API Automatizada COLINEAL"
        ]
        
        if conversation_history:
            description_parts.append(f"Conversación de {len(conversation_history)} mensajes")
        
        if extracted.get("product_interest"):
            description_parts.append(f"Productos de interés: {', '.join(extracted['product_interest'])}")
        
        if extracted.get("budget_range"):
            description_parts.append(f"Presupuesto mencionado: {extracted['budget_range']}")
        
        if extracted.get("urgency"):
            description_parts.append(f"Nivel de urgencia: {extracted['urgency']}")
        
        # Agregar resumen de conversación
        if conversation_history:
            description_parts.append("\n=== HISTORIAL DE CONVERSACIÓN ===")
            for i, msg in enumerate(conversation_history[-3:], 1):  # Últimos 3 mensajes
                msg_type = "Cliente" if msg.get("type") == "user" else "Asistente"
                description_parts.append(f"{i}. {msg_type}: {msg.get('message', '')[:100]}...")
        
        # SOLO CAMPOS BÁSICOS DE ODOO
        return {
            'name': self._generate_smart_lead_name(extracted, phone_number, lead_quality),
            'phone': phone_number,
            'contact_name': extracted.get('name'),
            'email_from': extracted.get('email'),
            'city': extracted.get('location'),
            'description': '\n'.join(description_parts),
            'priority': self._map_quality_to_priority(lead_quality)
        }
    
    # ===== MÉTODOS AUXILIARES =====
    
    def _generate_lead_name(self, extracted_data: Dict, phone_number: str) -> str:
        """Genera nombre para lead (método original)."""
        
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

    def _generate_smart_lead_name(self, extracted_data: Dict, phone_number: str, quality: str) -> str:
        """Genera nombre inteligente (NUEVO MÉTODO)."""
        
        name = extracted_data.get('name')
        products = extracted_data.get('product_interest', [])
        
        if name and products:
            main_product = products[0]
            return f"{name} - {main_product.title()} ({quality.upper()})"
        elif name:
            return f"{name} - Consulta ({quality.upper()})"
        elif products:
            main_product = products[0] 
            return f"Lead {quality.upper()} - {main_product.title()}"
        else:
            return f"Lead {quality.upper()} - {phone_number[-4:]}"

    def _map_urgency_to_priority(self, urgency: str) -> str:
        """Mapea urgencia a prioridad de Odoo."""
        mapping = {
            "high": "3",     # Alta prioridad
            "medium": "2",   # Media prioridad  
            "low": "1"       # Baja prioridad
        }
        return mapping.get(urgency, "1")

    def _map_quality_to_priority(self, quality: str) -> str:
        """Mapea calidad del lead a prioridad."""
        mapping = {
            "hot": "3",      # Alta prioridad
            "warm": "2",     # Media prioridad
            "cold": "1"      # Baja prioridad
        }
        return mapping.get(quality, "1")