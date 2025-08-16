# src/core/security.py
import hmac
import hashlib
import base64
from fastapi import Request
from typing import Dict

def validate_twilio_signature(
    token: str, signature: str, url: str, form_data: Dict
) -> bool:
    """
    Valida la firma de Twilio reconstruyendo el mensaje a partir de los datos del formulario.
    """
    if not signature:
        return False
    
    # Ordena los parámetros del formulario alfabéticamente y los concatena
    sorted_params = sorted(form_data.items())
    concatenated_params = "".join(f"{k}{v}" for k, v in sorted_params)
    
    # Crea el string completo que se va a firmar
    data_to_sign = f"{url}{concatenated_params}".encode()
    
    # Recrea la firma esperada usando el token
    expected_signature = hmac.new(
        key=token.encode(),
        msg=data_to_sign,
        digestmod=hashlib.sha1
    ).digest()
    
    expected_signature_b64 = base64.b64encode(expected_signature).decode()
    
    # Compara las firmas de manera segura
    return hmac.compare_digest(expected_signature_b64, signature)