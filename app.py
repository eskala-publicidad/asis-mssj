import os
import requests
from flask import Flask, request

app = Flask(__name__)

# Estas variables las configuraremos después en el Dashboard de Render
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
WIT_AI_TOKEN = os.environ.get('WIT_AI_TOKEN')

# DICCIONARIO DE MEMORIA: Aquí guardamos en qué parte del "mapa" va cada cliente
sesiones_usuarios = {}

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
                        
                        # Generamos la respuesta pasándole el ID del usuario y los datos de Wit
                        respuesta = generar_respuesta(sender_id, wit_response)
                        
                        # Enviamos el mensaje de vuelta
                        if respuesta:
                            send_message(sender_id, respuesta)
    return "ok", 200

def get_wit_response(text):
    headers = {'Authorization': f'Bearer {WIT_AI_TOKEN}'}
    # La fecha (v=...) asegura compatibilidad con la versión de la API
    resp = requests.get(f'https://api.wit.ai/message?v=20260320&q={text}', headers=headers)
    return resp.json()

def generar_respuesta(sender_id, wit_data):
    # Esto imprimirá la respuesta de Wit.ai en la consola de Render para depurar
    print("Datos recibidos de Wit.ai:", wit_data)
    
    # 1. Si el usuario es nuevo, lo ponemos en el nodo inicial del mapa
    if sender_id not in sesiones_usuarios:
        sesiones_usuarios[sender_id] = {'estado': 'inicio'}
        
    estado_actual = sesiones_usuarios[sender_id]['estado']
    
    intents = wit_data.get('intents', [])
    entities = wit_data.get('entities', {})
    top_intent = intents[0]['name'] if intents else None

    # ==========================================
    # NODO 1: EL INICIO DEL MAPA (Estado default)
    # ==========================================
    if estado_actual == 'inicio':
        
        if top_intent == 'consultar_precio:consultar_precio':
            modelo = entities.get('modelo:modelo', [{}])[0].get('value') if entities.get('modelo:modelo') else None
            if modelo:
                precio = obtener_precio(modelo)
                if precio:
                    return f"El precio del modelo {modelo} es ${precio}."
                else:
                    return "No tengo el costo exacto a la mano, pero te conectaré con un administrador para que te dé el precio actualizado."
            else:
                return "El precio de nuestras botas y zapatos varía según el modelo. ¿Buscas algún estilo en particular?"
            
        elif top_intent == 'ubicacion:ubicacion':
            return "Nos encontramos en San Francisco del Rincón, Guanajuato. ¡Será un gusto recibirte!"
            
        elif top_intent == 'comprar:comprar':
            modelo = entities.get('modelo', [{}])[0].get('value') if entities.get('modelo') else '[MODELO]'
            linea = entities.get('linea', [{}])[0].get('value') if entities.get('linea') else '[LINEA]'
            talla = entities.get('talla', [{}])[0].get('value') if entities.get('talla') else '[TALLA]'
            color = entities.get('color', [{}])[0].get('value') if entities.get('color') else '[COLOR]'
            mensaje = f"¡Excelente elección! Para finalizar tu pedido, haz clic en este enlace de WhatsApp: https://wa.me/524771474482?text=Hola,%20quiero%20comprar%20el%20Modelo:%20{modelo},%20Linea:%20{linea},%20Talla:%20{talla},%20Color:%20{color}. La información de envío la acordaremos por ese medio."
            return mensaje
            
        elif top_intent == 'contacto:contacto':
            return "DATOS DE CONTACTO GENERAL:\n- Web: www.calzadocaribu.com\n- WhatsApp Ventas: 4771474482\n- Correo: contacto@calzadocaribu.com"
            
        elif top_intent == 'productos:productos':
            # Avanzamos al usuario al nodo de catálogo
            sesiones_usuarios[sender_id]['estado'] = 'viendo_catalogo' 
            return """LÍNEAS DE PRODUCTO Y PRECIOS DESTACADOS:
1. LÍNEA WORK INYECCIÓN (Uso rudo/Industrial): 
   - Modelos: 332 ($715), 329 ($760), 110 ($760), 320 ($795), 321 ($840).
2. LÍNEA EXTREMO (Senderismo/Outdoor):
   - Modelos: 755 ($1,155), 720 ($1,155), 716 ($1,110), 711 ($1,090).
3. LÍNEA CASUAL:
   - Modelos: 322 ($795), 323 ($795), 415 ($740).
¿Te interesó alguno para pasarte el precio exacto o iniciar tu compra?"""
            
        elif top_intent == 'queja:queja':
            # Avanzamos en el mapa. Cambiamos el estado del usuario.
            sesiones_usuarios[sender_id]['estado'] = 'esperando_fotos_queja'
            return "Lamento la situación. Si tus botas se descocieron, despegaron o rompieron, por favor envíame por aquí fotografías del daño y tu recibo de compra para poder ayudarte."

        # Respuesta si el bot no detecta ninguna intención clara mientras está en 'inicio'
        return "Hola, soy Terneribu el asistente virtual. ¿En qué te puedo ayudar hoy? Opciones por defecto:\n- ¿Qué modelos tienes para el trabajo?\n- ¿Dónde se encuentran sus tiendas?\n- ¿Tienen página web?"

    # ==========================================
    # NODO 2: ESPERANDO FOTOS DE UNA QUEJA
    # ==========================================
    elif estado_actual == 'esperando_fotos_queja':
        # Sin importar lo que diga aquí (idealmente subió fotos), lo regresamos al inicio del mapa
        sesiones_usuarios[sender_id]['estado'] = 'inicio' 
        return "Gracias por la información, estamos analizando tu caso. En breve una persona se pondrá en contacto contigo para darte una solución."

    # ==========================================
    # NODO 3: VIENDO CATÁLOGO
    # ==========================================
    elif estado_actual == 'viendo_catalogo':
        if top_intent == 'comprar:comprar':
            # Termina el flujo de catálogo y regresa al inicio
            sesiones_usuarios[sender_id]['estado'] = 'inicio' 
            return "¡Perfecto! Vamos a armar tu pedido. ¿Qué modelo y talla te gustaron?"
        else:
            # Si hace otra pregunta que no sea comprar, lo devolvemos al inicio para que siga su camino
            sesiones_usuarios[sender_id]['estado'] = 'inicio'
            return "Si necesitas ver tallas o precios de algún modelo en específico, dímelo. O si tienes otra duda, aquí estoy."

    # Respuesta de seguridad general
    return "Disculpa, me perdí un poco. ¿Podrías repetirlo de otra manera?"

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