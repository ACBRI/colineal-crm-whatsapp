# 🚀 Colineal CRM WhatsApp API - Fase 2

## 🎯 **SISTEMA INTELIGENTE DE GESTIÓN DE LEADS**

Sistema avanzado que integra WhatsApp con Odoo CRM usando IA para clasificar y gestionar leads de manera inteligente.

### ✨ **NUEVAS CARACTERÍSTICAS - FASE 2:**

- 🤖 **Clasificador Inteligente**: Evalúa si hay información suficiente antes de crear leads
- 💬 **Gestión Conversacional**: Mantiene contexto entre mensajes y hace preguntas inteligentes
- 📊 **Analytics Avanzados**: Estadísticas de conversaciones y calidad de leads
- 🔄 **Flujo Adaptativo**: Se adapta según el tipo de consulta (ventas vs soporte)
- 📈 **Leads Enriquecidos**: Crea leads con información más completa y estructurada

---

## 🏗️ **ARQUITECTURA DEL SISTEMA**

```
WhatsApp → Twilio → FastAPI → AIClassifier → ConversationService → Odoo CRM
                              ↓
                         Redis (Estado)
```

### **Componentes Principales:**

1. **AIClassifier** (`src/services/ai_classifier.py`)
   - Analiza completitud de información
   - Determina acciones inteligentes
   - Genera preguntas de seguimiento

2. **ConversationService** (`src/services/conversation_service.py`)
   - Gestiona estado de conversaciones
   - Mantiene historial en Redis
   - Calcula métricas de completitud

3. **Webhook Inteligente** (`src/api/whatsapp_webhook.py`)
   - Procesamiento contextual de mensajes
   - Endpoints de gestión y analytics
   - Manejo de casos especiales

---

## 🚀 **INSTALACIÓN Y CONFIGURACIÓN**

### **1. Requisitos:**
```bash
Python 3.8+
Redis Server
Odoo 14+ con CRM
Cuenta Twilio (WhatsApp Business)
Google AI API Key
```

### **2. Instalar dependencias:**
```bash
pip install -r requirements.txt
```

### **3. Configurar variables de entorno (.env):**
```bash
# Google AI
GOOGLE_API_KEY=tu_api_key_de_google

# Twilio WhatsApp
TWILIO_AUTH_TOKEN=tu_token_de_twilio

# Odoo CRM
ODOO_URL=http://tu-servidor-odoo:8069
ODOO_DB=tu_base_de_datos
ODOO_USERNAME=tu_usuario
ODOO_PASSWORD=tu_contraseña

# Redis
REDIS_URL=redis://localhost:6379/0

# Opcional
ENVIRONMENT=development
```

### **4. Iniciar servicios:**
```bash
# Iniciar Redis
redis-server

# Iniciar la aplicación
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🧪 **PRUEBAS DEL SISTEMA**

### **Pruebas Automáticas:**
```bash
python test_fase2_system.py
```

### **Modo Interactivo:**
```bash
python test_fase2_system.py interactive
```

### **Verificar Estado:**
```bash
curl http://127.0.0.1:8000/system/status
```

---

## 📱 **FLUJO DE TRABAJO**

### **1. Mensaje Inicial:**
```
Cliente: "Hola, buenos días"
Sistema: ¿En qué puedo ayudarte hoy?
```

### **2. Recolección de Información:**
```
Cliente: "Busco sofás"
Sistema: ¿Podrías compartirme tu nombre para personalizar mejor la atención?
```

### **3. Cualificación:**
```
Cliente: "Soy María, necesito un sofá de 3 puestos"
Sistema: ¿Tienes algún presupuesto en mente?
```

### **4. Creación de Lead:**
```
Cliente: "Mi presupuesto es $2000"
Sistema: ¡Perfecto, María! He registrado tu interés en sofás. 
         Un asesor especializado te contactará pronto. ¡Gracias! 🏠✨
```

---

## 🔧 **ENDPOINTS PRINCIPALES**

### **Webhook Principal:**
```http
POST /api/webhook/whatsapp
Content-Type: application/x-www-form-urlencoded
X-Twilio-Signature: [firma_validada]

Body: datos del mensaje de WhatsApp
```

### **Gestión de Conversaciones:**
```http
# Estado de conversación
GET /api/conversation/{phone_number}/status

# Historial completo
GET /api/conversation/{phone_number}/history

# Reiniciar conversación
POST /api/conversation/{phone_number}/reset
```

### **Analytics:**
```http
# Estadísticas generales
GET /api/analytics/conversations

# Estado del sistema
GET /system/status

# Configuración
GET /system/config
```

---

## 📊 **ANALYTICS Y MONITOREO**

### **Métricas Disponibles:**
- Conversaciones activas vs completadas
- Tasa de conversión a leads
- Tiempo promedio de conversación
- Calidad de leads (hot/warm/cold)
- Efectividad del clasificador IA

### **Dashboard de Estado:**
```bash
# Ver estado en tiempo real
curl http://127.0.0.1:8000/system/status | jq

# Analytics de conversaciones
curl http://127.0.0.1:8000/api/analytics/conversations | jq
```

---

## 🧠 **INTELIGENCIA ARTIFICIAL**

### **Clasificación de Mensajes:**

**🔥 HOT (Alta Probabilidad):**
- Información de contacto completa
- Producto específico identificado
- Presupuesto mencionado
- Urgencia clara

**🟡 WARM (Media Probabilidad):**
- Alguna información de contacto
- Interés general en productos
- Consulta específica

**❄️ COLD (Baja Probabilidad):**
- Solo saludo
- Consulta muy vaga
- Falta información crítica

### **Acciones Inteligentes:**
- `create_lead`: Crear lead inmediatamente
- `ask_clarifying_question`: Pedir más detalles
- `request_contact_info`: Solicitar nombre/contacto
- `ask_about_interest`: Preguntar sobre productos
- `transfer_to_support`: Derivar a soporte
- `gather_more_details`: Completar información

---

## 🔒 **SEGURIDAD**

### **Validaciones Implementadas:**
- ✅ Verificación de firma HMAC de Twilio
- ✅ Prevención de mensajes duplicados
- ✅ Validación de datos de entrada
- ✅ Manejo seguro de errores
- ✅ Rate limiting implícito

### **Datos Sensibles:**
- Todas las credenciales en variables de entorno
- No se almacenan contraseñas en código
- Logs sin información personal

---

## 📈 **INTEGRACIÓN CON ODOO**

### **Campos de Lead Creados:**
```python
{
    'name': 'Nombre descriptivo del lead',
    'phone': 'Número de WhatsApp', 
    'contact_name': 'Nombre del contacto',
    'email_from': 'Email si se proporciona',
    'city': 'Ciudad mencionada',
    'description': 'Mensaje original + análisis IA',
    'priority': 'Prioridad basada en urgencia',
    'x_source': 'WhatsApp',
    'x_product_interest': 'Productos mencionados',
    'x_budget_range': 'Presupuesto mencionado',
    'x_ai_confidence': 'Nivel de confianza del análisis',
    'x_quality_score': 'hot/warm/cold'
}
```

### **Funciones Avanzadas:**
- Detección de leads duplicados
- Actualización de leads existentes
- Notas automáticas con análisis IA
- Estadísticas de leads por WhatsApp

---

## 🔧 **CONFIGURACIÓN AVANZADA**

### **Personalizar Clasificador:**
Editar `src/services/ai_classifier.py`:
```python
# Ajustar criterios mínimos
self.minimum_criteria = {
    "contact_info": ["name", "phone", "email"],
    "interest_level": ["product_interest", "specific_need"], 
    "intent_clarity": ["clear_intent"]
}
```

### **Personalizar Preguntas:**
Modificar diccionario `questions` en `_generate_next_question()`:
```python
questions = {
    "ask_clarifying_question": [
        "¿En qué puedo ayudarte hoy?",
        "¿Hay algo específico que te interese?"
    ]
}
```

### **Configurar TTL de Conversaciones:**
En `src/services/conversation_service.py`:
```python
self.conversation_ttl = 86400 * 7  # 7 días
```

---

## 🐛 **TROUBLESHOOTING**

### **Problemas Comunes:**

**❌ Error de conexión a Redis:**
```bash
# Verificar que Redis esté ejecutándose
redis-cli ping
# Respuesta esperada: PONG
```

**❌ Error de conexión a Odoo:**
```bash
# Probar conexión manualmente
python test_odoo_connection.py
```

**❌ Error de Google AI:**
```bash
# Verificar API key
echo $GOOGLE_API_KEY
```

### **Logs de Debugging:**
```bash
# Ver logs en tiempo real
tail -f logs/colineal.log

# Logs específicos del clasificador
grep "AIClassifier" logs/colineal.log
```

---

## 📚 **DOCUMENTACIÓN ADICIONAL**

### **API Documentation:**
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### **Arquitectura Técnica:**
- FastAPI + Pydantic para validación
- Redis para estado temporal
- OdooRPC para integración CRM
- Google Generative AI para análisis

### **Patrones de Diseño:**
- Repository Pattern (OdooService)
- Service Layer Architecture
- Dependency Injection
- Circuit Breaker Pattern (manejo de errores)

---

## 🚀 **PRÓXIMAS FUNCIONALIDADES**

### **Fase 3 (Planificada):**
- 📱 Respuestas automáticas inteligentes
- 🎯 Segmentación avanzada de leads
- 📊 Dashboard web en tiempo real
- 🤖 Chatbot conversacional completo
- 📈 Machine Learning para mejora continua

---

## 👥 **SOPORTE**

### **Contacto Técnico:**
- Documentación: `/docs`
- Estado del Sistema: `/system/status`
- Logs: Revisar archivos en `logs/`

### **Monitoreo:**
```bash
# Verificar estado cada 5 minutos
watch -n 300 'curl -s http://127.0.0.1:8000/system/status | jq .system_status'
```

---

## 📄 **LICENCIA**

Proyecto privado para Colineal - Todos los derechos reservados.

---

**🎉 ¡Sistema Fase 2 listo para producción!**