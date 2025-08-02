import json
import requests
from flask import Flask, request, jsonify

# --- Importaciones ---
from utils.load_catalog import load_catalog
from nlu.intent_classifier import classify_intent
from nlu.slot_filler import extract_slots

# --- 1. Inicialización ---
app = Flask(__name__)
AGENT_URL = "http://127.0.0.1:8000/predict"
print("🚀 Iniciando Orquestador del Agente de Revit (Modo Épico V5 - El Traductor)...")

# --- 2. Lógica de Traducción y Enriquecimiento de Prompt ---
def translate_to_explicit_prompt(user_text: str, intent: str, slots: dict, context: dict) -> str:
    """
    Re-escribe el prompt del usuario para ser explícito, usando el contexto de Revit.
    """
    prompt_parts = [user_text]

    # Lógica para completar información faltante crucial
    if intent in ['CreateWall', 'InsertFamilyInstance', 'CreateFloor']:
        # Añadir nivel si no está presente
        if 'level_name' not in slots and context.get('available_levels'):
            default_level = context['available_levels'][0]
            prompt_parts.append(f"en el nivel '{default_level}'")
            print(f"  -> Contexto añadido: Se usará el nivel '{default_level}'.")
            
        # Añadir tipo de muro si no está presente
        if intent == 'CreateWall' and 'family_type' not in slots and context.get('available_wall_types'):
            # Buscamos un tipo de muro genérico común en la lista de disponibles
            generic_type = next((wt for wt in context['available_wall_types'] if "Genérico" in wt or "Generic" in wt), None)
            if generic_type:
                prompt_parts.append(f"del tipo '{generic_type}'")
                print(f"  -> Contexto añadido: Se usará el tipo de muro '{generic_type}'.")

    # Une todas las partes en una sola frase coherente
    final_prompt = " ".join(prompt_parts)
    # Reemplaza dobles espacios por si acaso
    return ' '.join(final_prompt.split())

# --- 3. Función de Comunicación con el Agente LLM ---
def call_revit_agent(prompt: str) -> str:
    """
    Envía el prompt final al agente LLM y devuelve el código generado.
    """
    # ### CORRECCIÓN: ESTE BLOQUE FALTABA ###
    try:
        payload = {"prompt": prompt} 
        response = requests.post(AGENT_URL, json=payload, timeout=300)
        response.raise_for_status()
        response_json = response.json()
        return response_json.get("code", "// ERROR: La respuesta del agente no contiene la clave 'code'.")
    except requests.exceptions.RequestException as e:
        error_message = f"// ERROR: No se pudo conectar con el agente LLM en {AGENT_URL}. Revisa que el servidor del agente esté en funcionamiento. Detalles: {e}"
        print(f"💥 {error_message}")
        return error_message
    except Exception as e:
        error_message = f"// ERROR: Ocurrió un error inesperado al contactar al agente. Detalles: {e}"
        print(f"💥 {error_message}")
        return error_message
    # ### FIN DE LA CORRECCIÓN ###

# --- 4. Endpoint Principal de la API ---
@app.route("/process_instruction", methods=["POST"])
def process_instruction():
    try:
        data = request.json
        user_text = data.get("text", "").strip()
        revit_context = data.get("context", {})

        if not user_text: return jsonify({"error": "El campo 'text' no puede estar vacío."}), 400

        print(f"\n\n--- INICIO DE NUEVA PETICIÓN: '{user_text}' ---")
        if revit_context: print(f"Contexto recibido de Revit: {revit_context}")

        intent = classify_intent(user_text)
        slots = extract_slots(user_text, intent)
        print(f"1. NLU Completado -> Intención: [{intent}], Slots: {slots}")

        # FASE 2: TRADUCCIÓN A PROMPT EXPLÍCITO
        final_prompt = translate_to_explicit_prompt(user_text, intent, slots, revit_context)
        print(f"2. Prompt TRADUCIDO para Agente: '{final_prompt}'")

        # FASE 3: DELEGACIÓN
        generated_code = call_revit_agent(final_prompt)
        print("3. Código C# recibido del Agente.")

        # FASE 4: RESPUESTA
        final_response = { "intent": intent, "slots": slots, "generated_code": generated_code }
        print("--- FIN DE LA PETICIÓN ---")
        return jsonify(final_response)
    except Exception as e:
        print(f"💥 Ha ocurrido un error en el orquestador: {e}")
        return jsonify({"error": f"Error interno en el orquestador: {str(e)}"}), 500

# --- Arranque del Servidor ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)