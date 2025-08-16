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
        if self._odoo is None:
            parsed_url = urlparse(self.url)
            host = parsed_url.hostname
            port = parsed_url.port or 8069
            
            self._odoo = odoorpc.ODOO(host, port=port)
            self._odoo.login(self.db, self.username, self.password)
        return self._odoo
        
    def test_connection(self) -> bool:
        try:
            odoo = self._get_connection()
            print("✅ Conexión exitosa!")
            return True
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
    
    def create_lead_from_whatsapp(self, phone_number: str, message: str, ai_analysis: dict):
        """Crea un lead en Odoo desde WhatsApp"""
        try:
            odoo = self._get_connection()
            
            # Crear los datos del lead
            lead_data = {
                'name': f"Lead WhatsApp - {phone_number}",
                'phone': phone_number,
                'description': f"Mensaje: {message}\n\nAnálisis IA: {ai_analysis.get('intent', 'Sin análisis')}",
            }
            
            # Crear el lead
            lead_id = odoo.env['crm.lead'].create(lead_data)
            print(f"✅ Lead creado con ID: {lead_id}")
            return lead_id
            
        except Exception as e:
            print(f"❌ Error creando lead: {str(e)}")
            return None