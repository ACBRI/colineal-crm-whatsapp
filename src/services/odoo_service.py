# src/services/odoo_service.py
import json
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse
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
            # Realizar una consulta simple para verificar conectividad
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
        Crea un lead mejorado en Odoo desde WhatsApp con datos enriquecidos por IA.
        """
        try:
            odoo = self._get_connection()
            
            # Si no se proporcionan datos formateados, usar el método legacy
            if not lead_data:
                lead_data = self._create_legacy_lead_data(phone_number, message, ai_analysis)
            
            # Validar y limpiar datos antes de enviar
            validated_data = self._validate_lead_data(lead_data)
            
            # Buscar si ya existe un lead para este número
            existing_lead = self._find_existing_lead(phone_number)
            
            if existing_lead:
                # Actualizar lead existente en lugar de crear uno nuevo
                return self._update_existing_lead(existing_lead, validated_data, message, ai_analysis)
            else:
                # Crear nuevo lead
                lead_id = odoo.env['crm.lead'].create(validated_data)
                
                # Agregar nota con el mensaje original
                self._add_message_note(lead_id, message, ai_analysis)
                
                logger.info(f"✅ Lead creado exitosamente con ID: {lead_id}")
                return lead_id
                
        except Exception as e:
            logger.error(f"❌ Error creando lead en Odoo: {str(e)}")
            raise Exception(f"Error creando lead: {str(e)}")
    
    def _validate_lead_data(self, lead_data: dict) -> dict:
        """Valida y limpia los datos del lead antes de enviarlos a Odoo."""
        
        # Campos base requeridos por Odoo
        validated = {
            'name': lead_data.get('name', 'Lead WhatsApp Sin Nombre'),
            'phone': lead_data.get('phone', ''),
        }
        
        # Campos opcionales comunes
        optional_fields = [
            'contact_name', 'email_from', 'city', 'description', 
            'priority', 'user_id', 'team_id', 'source_id'
        ]
        
        for field in optional_fields:
            if lead_data.get(field):
                validated[field] = lead_data[field]
        
        # Campos personalizados (solo agregar si existen en la instalación de Odoo)
        # Estos campos se agregarán solo si no causan errores
        custom_fields = {
            'x_source': lead_data.get('x_source'),
            'x_product_interest': lead_data.get('x_product_interest'),
            'x_budget_range': lead_data.get('x_budget_range'),
            'x_ai_confidence': lead_data.get('x_ai_confidence'),
            'x_quality_score': lead_data.get('x_quality_score'),
            'x_whatsapp_phone': lead_data.get('phone')  # Backup del teléfono
        }
        
        # Solo agregar campos personalizados si tienen valor
        for field, value in custom_fields.items():
            if value is not None:
                validated[field] = value
        
        return validated
    
    def _find_existing_lead(self, phone_number: str) -> Optional[int]:
        """Busca si ya existe un lead para este número de teléfono."""
        
        try:
            odoo = self._get_connection()
            
            # Limpiar número para búsqueda
            clean_phone = phone_number.replace("whatsapp:", "").replace("+", "").replace(" ", "")
            
            # Buscar por teléfono exacto o similar
            existing_leads = odoo.env['crm.lead'].search([
                '|',
                ('phone', 'ilike', clean_phone),
                ('mobile', 'ilike', clean_phone)
            ], limit=1)
            
            return existing_leads[0] if existing_leads else None
            
        except Exception as e:
            logger.warning(f"Error buscando lead existente: {e}")
            return None
    
    def _update_existing_lead(
        self, 
        lead_id: int, 
        new_data: dict, 
        message: str, 
        ai_analysis: dict
    ) -> int:
        """Actualiza un lead existente con nueva información."""
        
        try:
            odoo = self._get_connection()
            
            # Obtener datos actuales del lead
            current_lead = odoo.env['crm.lead'].read(lead_id, ['description', 'name'])
            
            # Actualizar solo campos que aporten nueva información
            update_data = {}
            
            # Actualizar descripción agregando el nuevo mensaje
            current_description = current_lead.get('description', '') or ''
            new_message_section = f"\n\n--- Nuevo mensaje ({json.dumps(datetime.now(), default=str)}) ---\n{message}\nAnálisis: {ai_analysis.get('intent', 'N/A')}"
            update_data['description'] = current_description + new_message_section
            
            # Actualizar otros campos si aportan información nueva
            if new_data.get('contact_name') and 'Sin Nombre' in current_lead.get('name', ''):
                update_data['name'] = new_data['name']
            
            if new_data.get('email_from'):
                update_data['email_from'] = new_data['email_from']
            
            if new_data.get('city'):
                update_data['city'] = new_data['city']
            
            # Actualizar el lead
            odoo.env['crm.lead'].write(lead_id, update_data)
            
            # Agregar nota sobre la actualización
            self._add_message_note(lead_id, f"Lead actualizado con nueva información: {message}", ai_analysis)
            
            logger.info(f"✅ Lead {lead_id} actualizado exitosamente")
            return lead_id
            
        except Exception as e:
            logger.error(f"Error actualizando lead {lead_id}: {e}")
            raise
    
    def _add_message_note(self, lead_id: int, message: str, ai_analysis: dict):
        """Agrega una nota al lead con el mensaje y análisis de IA."""
        
        try:
            odoo = self._get_connection()
            
            # Crear mensaje/nota en el lead
            note_body = f"""
            <p><strong>Mensaje de WhatsApp:</strong></p>
            <p>{message}</p>
            
            <p><strong>Análisis de IA:</strong></p>
            <ul>
                <li><strong>Intención:</strong> {ai_analysis.get('intent', 'N/A')}</li>
                <li><strong>Calidad:</strong> {ai_analysis.get('quality_assessment', 'N/A')}</li>
                <li><strong>Confianza:</strong> {ai_analysis.get('confidence_score', 'N/A')}</li>
                <li><strong>Productos de interés:</strong> {', '.join(ai_analysis.get('extracted_data', {}).get('product_interest', []))}</li>
            </ul>
            """
            
            # En versiones modernas de Odoo, usar mail.message
            odoo.env['mail.message'].create({
                'model': 'crm.lead',
                'res_id': lead_id,
                'message_type': 'comment',
                'body': note_body,
                'subtype_xmlid': 'mail.mt_note'
            })
            
        except Exception as e:
            logger.warning(f"No se pudo agregar nota al lead {lead_id}: {e}")
    
    def _create_legacy_lead_data(self, phone_number: str, message: str, ai_analysis: dict) -> dict:
        """Crea datos de lead usando el método legacy para compatibilidad."""
        
        return {
            'name': f"Lead WhatsApp - {phone_number}",
            'phone': phone_number,
            'description': f"Mensaje: {message}\n\nAnálisis IA: {ai_analysis.get('intent', 'Sin análisis')}",
            'x_source': 'WhatsApp',
            'priority': '1'  # Prioridad normal por defecto
        }
    
    def get_lead_info(self, lead_id: int) -> Optional[dict]:
        """Obtiene información de un lead específico."""
        
        try:
            odoo = self._get_connection()
            
            lead_data = odoo.env['crm.lead'].read(lead_id, [
                'name', 'phone', 'email_from', 'contact_name', 
                'city', 'description', 'stage_id', 'user_id',
                'create_date', 'priority'
            ])
            
            return lead_data[0] if lead_data else None
            
        except Exception as e:
            logger.error(f"Error obteniendo información del lead {lead_id}: {e}")
            return None
    
    def search_leads_by_phone(self, phone_number: str) -> list:
        """Busca todos los leads asociados a un número de teléfono."""
        
        try:
            odoo = self._get_connection()
            
            clean_phone = phone_number.replace("whatsapp:", "").replace("+", "").replace(" ", "")
            
            lead_ids = odoo.env['crm.lead'].search([
                '|',
                ('phone', 'ilike', clean_phone),
                ('mobile', 'ilike', clean_phone)
            ])
            
            if lead_ids:
                return odoo.env['crm.lead'].read(lead_ids, [
                    'id', 'name', 'phone', 'stage_id', 'create_date'
                ])
            
            return []
            
        except Exception as e:
            logger.error(f"Error buscando leads por teléfono {phone_number}: {e}")
            return []
    
    def get_lead_statistics(self) -> dict:
        """Obtiene estadísticas básicas de leads de WhatsApp."""
        
        try:
            odoo = self._get_connection()
            
            # Buscar leads de WhatsApp
            whatsapp_leads = odoo.env['crm.lead'].search_count([
                ('x_source', '=', 'WhatsApp')
            ])
            
            # Leads por etapa
            stages = odoo.env['crm.stage'].search_read([], ['id', 'name'])
            stage_stats = {}
            
            for stage in stages:
                count = odoo.env['crm.lead'].search_count([
                    ('x_source', '=', 'WhatsApp'),
                    ('stage_id', '=', stage['id'])
                ])
                stage_stats[stage['name']] = count
            
            return {
                'total_whatsapp_leads': whatsapp_leads,
                'leads_by_stage': stage_stats
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {'error': str(e)}

# Importar datetime para timestamps
from datetime import datetime