# src/services/odoo_service.py (VERSIÓN ULTRA BÁSICA - SOLO CAMPOS GARANTIZADOS)
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime
import odoorpc

logger = logging.getLogger(__name__)

class OdooService:
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self._odoo = None
        
    def _get_connection(self):
        """Establece conexión con Odoo."""
        if self._odoo is None:
            parsed_url = urlparse(self.url)
            host = parsed_url.hostname
            port = parsed_url.port or 8069
            
            self._odoo = odoorpc.ODOO(host, port=port)
            self._odoo.login(self.db, self.username, self.password)
        return self._odoo
        
    def test_connection(self) -> bool:
        """Prueba la conexión con Odoo."""
        try:
            odoo = self._get_connection()
            odoo.env['res.users'].search_count([])
            print("✅ Conexión exitosa con Odoo!")
            return True
        except Exception as e:
            print(f"❌ Error conectando con Odoo: {str(e)}")
            return False
    
    def create_lead_from_whatsapp(
        self, 
        phone_number: str, 
        message: str, 
        ai_analysis: dict,
        lead_data: dict = None
    ):
        """
        Crea un lead en Odoo usando SOLO campos básicos garantizados.
        """
        try:
            odoo = self._get_connection()
            
            # Si no se proporcionan datos formateados, usar el método legacy
            if not lead_data:
                lead_data = self._create_legacy_lead_data(phone_number, message, ai_analysis)
            
            # Validar y limpiar datos usando SOLO campos básicos
            validated_data = self._validate_basic_lead_data(lead_data)
            
            # Buscar si ya existe un lead para este número
            existing_lead_id = self._find_existing_lead(phone_number)
            
            if existing_lead_id:
                # Actualizar lead existente
                return self._update_existing_lead_basic(existing_lead_id, validated_data, message, ai_analysis)
            else:
                # Crear nuevo lead
                lead_id = odoo.env['crm.lead'].create(validated_data)
                
                # Agregar nota con el mensaje original
                self._add_message_note_basic(lead_id, message, ai_analysis)
                
                logger.info(f"✅ Lead creado exitosamente con ID: {lead_id}")
                return lead_id
                
        except Exception as e:
            logger.error(f"❌ Error creando lead en Odoo: {str(e)}")
            raise Exception(f"Error creando lead: {str(e)}")
    
    def _validate_basic_lead_data(self, lead_data: dict) -> dict:
        """Valida datos usando SOLO campos básicos de Odoo que SIEMPRE existen."""
        
        # CAMPOS BÁSICOS MÍNIMOS QUE EXISTEN EN TODA INSTALACIÓN DE ODOO
        validated = {}
        
        # CAMPO OBLIGATORIO
        validated['name'] = lead_data.get('name', 'Lead WhatsApp Sin Nombre')
        
        # CAMPOS OPCIONALES BÁSICOS (solo agregar si tienen valor)
        basic_optional_fields = {
            'contact_name': lead_data.get('contact_name'),     # Nombre del contacto
            'email_from': lead_data.get('email_from'),         # Email
            'phone': lead_data.get('phone'),                   # Teléfono
            'mobile': lead_data.get('mobile'),                 # Móvil  
            'city': lead_data.get('city'),                     # Ciudad
            'description': lead_data.get('description'),       # Descripción
            'priority': lead_data.get('priority', '1'),        # Prioridad (como string)
        }
        
        # Solo agregar campos que tienen valor real
        for field, value in basic_optional_fields.items():
            if value is not None and str(value).strip():
                validated[field] = value
        
        return validated
    
    def _find_existing_lead(self, phone_number: str) -> Optional[int]:
        """Busca si ya existe un lead para este número de teléfono."""
        
        try:
            odoo = self._get_connection()
            
            # Limpiar número para búsqueda
            clean_phone = phone_number.replace("whatsapp:", "").replace("+", "").replace(" ", "")
            
            # Buscar solo por phone (campo más básico)
            existing_leads = odoo.env['crm.lead'].search([
                ('phone', 'ilike', clean_phone)
            ], limit=1)
            
            return existing_leads[0] if existing_leads else None
            
        except Exception as e:
            logger.warning(f"Error buscando lead existente: {e}")
            return None
    
    def _update_existing_lead_basic(
        self, 
        lead_id: int, 
        new_data: dict, 
        message: str, 
        ai_analysis: dict
    ) -> int:
        """
        Actualiza un lead existente usando SOLO campos básicos.
        """
        
        try:
            odoo = self._get_connection()
            
            # Obtener datos actuales del lead (solo campos básicos)
            current_lead_data = odoo.env['crm.lead'].read(lead_id, ['description', 'name'])
            
            # Manejar respuesta (puede ser lista o dict)
            if isinstance(current_lead_data, list):
                current_lead = current_lead_data[0] if current_lead_data else {}
            else:
                current_lead = current_lead_data
            
            # Preparar datos de actualización
            update_data = {}
            
            # Actualizar descripción agregando el nuevo mensaje
            current_description = current_lead.get('description', '') or ''
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            new_message_section = f"\n\n--- Mensaje WhatsApp ({timestamp}) ---\n{message}\nAnálisis: {self._extract_basic_analysis(ai_analysis)}"
            update_data['description'] = current_description + new_message_section
            
            # Actualizar nombre si es genérico
            current_name = current_lead.get('name', '')
            if new_data.get('contact_name') and ('Sin Nombre' in current_name or 'WhatsApp' in current_name):
                update_data['name'] = new_data.get('name', current_name)
            
            # Actualizar otros campos básicos si tienen valor
            basic_updatable_fields = ['email_from', 'city', 'contact_name']
            for field in basic_updatable_fields:
                if new_data.get(field):
                    update_data[field] = new_data[field]
            
            # Actualizar el lead
            if update_data:
                odoo.env['crm.lead'].write(lead_id, update_data)
            
            logger.info(f"✅ Lead {lead_id} actualizado exitosamente")
            return lead_id
            
        except Exception as e:
            logger.error(f"Error actualizando lead {lead_id}: {e}")
            raise
    
    def _extract_basic_analysis(self, ai_analysis: dict) -> str:
        """Extrae resumen básico del análisis de IA."""
        
        try:
            if isinstance(ai_analysis, dict):
                # Obtener datos de análisis (estructura flexible)
                analysis_data = ai_analysis.get('analysis', ai_analysis)
                extracted_data = analysis_data.get('extracted_data', {})
                
                intent = extracted_data.get('intent', 'Sin análisis')
                quality = analysis_data.get('quality_assessment', 'N/A')
                
                return f"Intención: {intent}, Calidad: {quality}"
            
            return 'Sin análisis disponible'
        except:
            return 'Error procesando análisis'
    
    def _add_message_note_basic(self, lead_id: int, message: str, ai_analysis: dict):
        """Agrega una nota básica al lead."""
        
        try:
            odoo = self._get_connection()
            
            # Extraer análisis básico
            analysis_summary = self._extract_basic_analysis(ai_analysis)
            
            # Crear nota simple usando descripción (método más compatible)
            try:
                # Obtener descripción actual
                current_lead_data = odoo.env['crm.lead'].read(lead_id, ['description'])
                
                if isinstance(current_lead_data, list):
                    current_lead = current_lead_data[0] if current_lead_data else {}
                else:
                    current_lead = current_lead_data
                
                current_desc = current_lead.get('description', '') or ''
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                note_text = f"\n\n--- Nota Automática ({timestamp}) ---\nMensaje: {message}\nAnálisis: {analysis_summary}\nFuente: WhatsApp"
                new_desc = current_desc + note_text
                
                # Actualizar descripción
                odoo.env['crm.lead'].write(lead_id, {'description': new_desc})
                logger.info(f"✅ Nota básica agregada al lead {lead_id}")
                
            except Exception as note_error:
                logger.warning(f"No se pudo agregar nota al lead {lead_id}: {note_error}")
            
        except Exception as e:
            logger.warning(f"Error general agregando nota al lead {lead_id}: {e}")
    
    def _create_legacy_lead_data(self, phone_number: str, message: str, ai_analysis: dict) -> dict:
        """Crea datos de lead usando solo campos básicos."""
        
        analysis_summary = self._extract_basic_analysis(ai_analysis)
        
        return {
            'name': f"Lead WhatsApp - {phone_number}",
            'phone': phone_number,
            'description': f"Mensaje desde WhatsApp:\n{message}\n\nAnálisis IA: {analysis_summary}\nFuente: WhatsApp API",
            'priority': '1',  # String, no número
            'contact_name': None,  # Se extraerá del análisis si está disponible
        }
    
    def get_lead_info(self, lead_id: int) -> Optional[dict]:
        """Obtiene información básica de un lead."""
        
        try:
            odoo = self._get_connection()
            
            # Solo campos básicos garantizados
            basic_fields = [
                'name', 'contact_name', 'email_from', 'phone', 'mobile',
                'city', 'description', 'create_date', 'priority'
            ]
            
            lead_data = odoo.env['crm.lead'].read(lead_id, basic_fields)
            
            # Manejar respuesta
            if isinstance(lead_data, list):
                return lead_data[0] if lead_data else None
            else:
                return lead_data
            
        except Exception as e:
            logger.error(f"Error obteniendo información del lead {lead_id}: {e}")
            return None
    
    def search_leads_by_phone(self, phone_number: str) -> list:
        """Busca leads por teléfono usando campos básicos."""
        
        try:
            odoo = self._get_connection()
            
            clean_phone = phone_number.replace("whatsapp:", "").replace("+", "").replace(" ", "")
            
            # Búsqueda básica solo por phone
            lead_ids = odoo.env['crm.lead'].search([
                ('phone', 'ilike', clean_phone)
            ])
            
            if lead_ids:
                leads_data = odoo.env['crm.lead'].read(lead_ids, [
                    'id', 'name', 'contact_name', 'phone', 'create_date'
                ])
                return leads_data if isinstance(leads_data, list) else [leads_data]
            
            return []
            
        except Exception as e:
            logger.error(f"Error buscando leads por teléfono {phone_number}: {e}")
            return []
    
    def get_lead_statistics(self) -> dict:
        """Obtiene estadísticas básicas de leads de WhatsApp."""
        
        try:
            odoo = self._get_connection()
            
            # Buscar leads que mencionen WhatsApp en nombre o descripción
            whatsapp_leads = odoo.env['crm.lead'].search_count([
                '|',
                ('name', 'ilike', 'WhatsApp'),
                ('description', 'ilike', 'WhatsApp')
            ])
            
            return {
                'total_whatsapp_leads': whatsapp_leads,
                'message': 'Estadísticas básicas de WhatsApp'
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}