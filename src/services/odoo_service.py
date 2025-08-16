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
        
    def test_connection(self) -> bool:
        try:
            parsed_url = urlparse(self.url)
            host = parsed_url.hostname
            port = parsed_url.port or 8069
            
            print(f"Conectando a: {host}:{port}")
            
            self._odoo = odoorpc.ODOO(host, port=port)
            self._odoo.login(self.db, self.username, self.password)
            
            print("✅ Conexión exitosa!")
            return True
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False