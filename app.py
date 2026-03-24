import os
import requests
from flask import Flask, request

app = Flask(__name__)

# Estas variables las configuraremos después en el Dashboard de Render
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
WIT_AI_TOKEN = os.environ.get('WIT_AI_TOKEN')

# 1. Endpoint para que Meta verifique el Webhook
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return "Token de verificación incorrecto", 403
        return request.args["hub.challenge"], 200
    return "Servidor activo", 200

# 2. Endpoint para recibir los mensajes de los clientes
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry.get('messaging', []):
                if messaging_event.get('message'):
                    sender_id = messaging_event['sender']['id']
                    message_text = messaging_event['message'].get('text')
                    
                    if message_text:
                        # Consultamos a Wit.ai
                        wit_response = get_wit_response(message_text)
                        # Generamos la respuesta según la intención
                        respuesta = generar_respuesta(wit_response)
                        # Enviamos el mensaje de vuelta
                        send_message(sender_id, respuesta)
    return "ok", 200

def get_wit_response(text):
    headers = {'Authorization': f'Bearer {WIT_AI_TOKEN}'}
    # La fecha (v=...) asegura compatibilidad con la versión de la API
    resp = requests.get(f'https://api.wit.ai/message?v=20260320&q={text}', headers=headers)
    return resp.json()

def generar_respuesta(wit_data):
    # Esto imprimirá la respuesta de Wit.ai en la consola de Render para ayudarte a depurar
    print("Datos recibidos de Wit.ai:", wit_data)
    
    intents = wit_data.get('intents', [])
    entities = wit_data.get('entities', {})
    
    if intents:
        top_intent = intents[0]['name']
        
        # Asegúrate de que estos nombres sean EXACTAMENTE iguales a los de Wit.ai
        if top_intent == 'consultar_precio':
            # Verificar si hay entidad de modelo
            modelo = entities.get('modelo', [{}])[0].get('value') if entities.get('modelo') else None
            if modelo:
                precio = obtener_precio(modelo)
                if precio:
                    return f"El precio del modelo {modelo} es ${precio}."
                else:
                    return "No tengo el costo exacto a la mano, pero te conectaré con un administrador para que te dé el precio actualizado."
            else:
                return "El precio de nuestras botas y zapatos varía según el modelo. ¿Buscas algún estilo en particular?"
        elif top_intent == 'ubicacion':
            return "Nos encontramos en San Francisco del Rincón, Guanajuato. ¡Será un gusto recibirte!"
        elif top_intent == 'comprar':
            # Extraer entidades para el formato de compra
            modelo = entities.get('modelo', [{}])[0].get('value') if entities.get('modelo') else '[MODELO]'
            linea = entities.get('linea', [{}])[0].get('value') if entities.get('linea') else '[LINEA]'
            talla = entities.get('talla', [{}])[0].get('value') if entities.get('talla') else '[TALLA]'
            color = entities.get('color', [{}])[0].get('value') if entities.get('color') else '[COLOR]'
            mensaje = f"¡Excelente elección! Para finalizar tu pedido, haz clic en este enlace de WhatsApp: https://wa.me/524771474482?text=Hola,%20quiero%20comprar%20el%20Modelo:%20{modelo},%20Linea:%20{linea},%20Talla:%20{talla},%20Color:%20{color}. La información de envío la acordaremos por ese medio."
            return mensaje
        elif top_intent == 'contacto':
            return "DATOS DE CONTACTO GENERAL:\n- Web: www.calzadocaribu.com\n- WhatsApp Ventas: 4771474482\n- Correo: contacto@calzadocaribu.com"
        elif top_intent == 'productos':
            return """LÍNEAS DE PRODUCTO Y PRECIOS DESTACADOS:
1. LÍNEA WORK INYECCIÓN (Uso rudo/Industrial): 
   - Modelos: 332 ($715), 329 ($760), 110 ($760), 320 ($795), 321 ($840).
   - Características: Suela de poliuretano directa al corte, ligeros, ergonómicos.
2. LÍNEA EXTREMO (Senderismo/Outdoor):
   - Modelos: 755 ($1,155), 720 ($1,155), 716 ($1,110), 711 ($1,090).
   - Características: Suela de hule, máxima tracción, ideales para montaña.
3. LÍNEA CASUAL:
   - Modelos: 322 ($795), 323 ($795), 415 ($740).
   - Características: Comodidad diaria con estilo Caribú."""
        elif top_intent == 'queja':
            return "Si reportas que se descocieron, despegaron o rompieron, pide amablemente fotografías del daño y el recibo de compra. Una vez que el cliente diga que los tiene o los envíe, responde: 'Gracias por la información, estamos analizando tu caso. En breve una persona se pondrá en contacto contigo para darte una solución.'"
            
    return "Hola, soy Terneribu el asistente virtual. ¿En qué te puedo ayudar hoy? Opciones por defecto:\n- ¿Qué modelos tienes para el trabajo?\n- ¿Dónde se encuentran sus tiendas?\n- ¿Tienen página web?"

def obtener_precio(modelo):
    precios = {
        '332': 715, '329': 760, '110': 760, '320': 795, '321': 840,
        '755': 1155, '720': 1155, '716': 1110, '711': 1090,
        '322': 795, '323': 795, '415': 740
    }
    return precios.get(modelo)

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(port=5000, debug=True)