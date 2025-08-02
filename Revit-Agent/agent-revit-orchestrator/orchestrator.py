import os
import sys
import json
import requests
import logging
import re
from flask import Flask, request, jsonify

# --- 0. Configuración ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, REPO_ROOT)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OrchestratorAgent")

from shared_libs.nlu.intent_classifier import classify_intent
from shared_libs.nlu.slot_filler import extract_slots

# --- 1. Inicialización ---
app = Flask(__name__)
AGENT_URL = "http://localhost:8000/predict"
logger.info(f"✅ Orquestador (Modo Prompt Maker) iniciado. Apuntando al Coder en: {AGENT_URL}")

# --- 2. Lógica de Negocio ---

def build_expert_prompt(user_text: str, intent: str, slots: dict, revit_context: dict) -> str:
    """
    Construye un prompt de alta calidad, enriquecido con contexto, para que el Coder razone.
    """
    prompt = "### INSTRUCTION:\n"
    prompt += "You are an expert C# programmer for the Autodesk Revit API. Your task is to generate a C# code snippet that can be executed directly to fulfill the user's request.\n"
    prompt += "Analyze all the provided context and generate only the necessary C# code.\n"
    prompt += "Do not include explanations, comments, or markdown formatting like ```csharp.\n"
    
    # --- CONTEXTO ESTRUCTURADO ---
    prompt += "\n--- CONTEXT ---\n"
    prompt += f"User's Natural Language Request: '{user_text}'\n"
    
    if intent != "Unknown":
        prompt += f"System's Intent Analysis: {intent}\n"
    if slots:
        # Formateamos los slots para que sean más legibles para el LLM
        formatted_slots = ", ".join([f"{k}: '{v}'" for k, v in slots.items()])
        prompt += f"Key Parameters Extracted: {formatted_slots}\n"
    
    # Esta es la clave: el contexto que vendría del plugin de Revit
    if revit_context.get("available_levels"):
        prompt += f"Available Levels in Project: {', '.join(revit_context['available_levels'])}\n"
    if revit_context.get("available_wall_types"):
        prompt += f"Available Wall Types in Project: {', '.join(revit_context['available_wall_types'])}\n"
    if revit_context.get("selected_element_ids"):
        prompt += f"User's Selected Element IDs: {', '.join(revit_context['selected_element_ids'])}\n"
        
    prompt += "\n### RESPONSE:\n"
    return prompt

def call_coder_agent(prompt: str) -> dict:
    try:
        payload = {"prompt": prompt}
        response = requests.post(AGENT_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json() 
    except requests.exceptions.RequestException as e:
        logger.error(f"No se pudo conectar con el Coder en {AGENT_URL}. {e}")
        return {"code": f"// ERROR: No se pudo conectar con el Coder."}

def clean_generated_code(raw_code: str) -> str:
    """
    Extrae el código C# de la salida del LLM, eliminando explicaciones y formato.
    """
    if not isinstance(raw_code, str):
        return ""
        
    code_to_process = raw_code # Empezamos con el texto crudo
    
    # 1. Buscar bloques de código ```csharp ... ```
    code_blocks = re.findall(r'```(?:csharp|C#)?\n(.*?)\n```', raw_code, re.DOTALL)
    if code_blocks:
        # Si encuentra bloques, nos quedamos con el contenido del PRIMERO como nuestro texto a procesar
        code_to_process = code_blocks[0]
    
    # Limpieza adicional si el modelo añade explicaciones fuera del bloque
    if "### RESPONSE:" in code_to_process:
        code_to_process = code_to_process.split("### RESPONSE:")[1]
    if "### INSTRUCTION:" in code_to_process:
        code_to_process = code_to_process.split("### INSTRUCTION:")[0]

    # 2. Si es una clase IExternalCommand, extrae solo el contenido del método Execute
    execute_content_match = re.search(r'public Result Execute\s*\(.*\)\s*\{([\s\S]*?)\s*return Result\.Succeeded;\s*\}', code_to_process, re.DOTALL)
    if execute_content_match:
        inner_code = execute_content_match.group(1).strip()
        
        transaction_content_match = re.search(r'using\s*\(\s*Transaction.*\)\s*\{([\s\S]*)\}', inner_code, re.DOTALL)
        if transaction_content_match:
            return transaction_content_match.group(1).strip()
        
        transaction_match = re.search(r't\.Start\(\);([\s\S]*)t\.Commit\(\);', inner_code, re.DOTALL)
        if transaction_match:
            return transaction_match.group(1).strip()
            
        return inner_code
    
    return code_to_process.strip()

# --- 3. Endpoint Principal ---
@app.route("/process_instruction", methods=["POST"])
def process_instruction():
    try:
        data = request.json
        user_text = data.get("text", "").strip()
        revit_context = data.get("context", {}) # El contexto del plugin

        logger.info(f"--- INICIO DE PETICIÓN: '{user_text}' ---")
        
        # FASE 1: NLU
        intent = classify_intent(user_text)
        slots = extract_slots(user_text, intent)
        logger.info(f"1. NLU -> Intención: [{intent}], Slots: {slots}")

        # FASE 2: Construcción del Prompt Experto
        final_prompt = build_expert_prompt(user_text, intent, slots, revit_context)
        logger.info(f"2. Prompt Experto construido para el Coder.")

        # FASE 3: Delegación
        coder_response = call_coder_agent(final_prompt)
        raw_code = coder_response.get("code", "// ERROR: El Coder no devolvió código.")
        final_code = clean_generated_code(raw_code)
        logger.info(f"3. Código recibido y limpiado.")

        # FASE 4: Respuesta
        return jsonify({
            "intent": intent,
            "slots": slots,
            "generated_code": final_code
        })
        
    except Exception as e:
        logger.error(f"Error inesperado en el orquestador: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)