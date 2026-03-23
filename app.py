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
    if intents:
        top_intent = intents[0]['name']
        
        # Asegúrate de que estos nombres sean EXACTAMENTE iguales a los de Wit.ai
        if top_intent == 'consultar_precio':
            return "El precio de nuestras botas y zapatos varía según el modelo. ¿Buscas algún estilo en particular?"
        elif top_intent == 'ubicacion':
            return "Nos encontramos en San Francisco del Rincón, Guanajuato. ¡Será un gusto recibirte!"
        elif top_intent == 'comprar':
            return "¡Excelente! Puedes realizar tu pedido por aquí mismo o te comparto el catálogo."
            
    return "Hola, soy el asistente virtual. ¿En qué te puedo ayudar hoy?"

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(port=5000, debug=True)