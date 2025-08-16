# src/services/twilio_service.py
import os
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.client = Client(self.account_sid, self.auth_token)
        self.whatsapp_from = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    
    def send_whatsapp_message(self, to_number: str, message: str) -> bool:
        """Envía un mensaje de WhatsApp usando Twilio."""
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.whatsapp_from,
                to=to_number
            )
            logger.info(f"✅ Mensaje enviado a {to_number}: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje a {to_number}: {e}")
            return False

# Instancia global
twilio_service = TwilioService()