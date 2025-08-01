import os
import sys
import json
import requests
import logging
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from flask import Flask, request, jsonify

# --- 0. Configuración del Logging y Rutas ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OrchestratorAgent")

# Asumimos que el contenedor se inicia con la raíz del proyecto montada en /app
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SHARED_LIBS_PATH = os.path.join(REPO_ROOT, 'shared_libs')
sys.path.insert(0, REPO_ROOT)

from shared_libs.nlu.intent_classifier import classify_intent
from shared_libs.nlu.slot_filler import extract_slots

# --- 1. Inicialización de la App y Componentes RAG ---
app = Flask(__name__)
AGENT_URL = "http://revit-code:8000/predict" # Nombre del servicio de Docker

# Rutas a los archivos del RAG
DATA_DIR = os.path.join(REPO_ROOT, 'Revit-Agent', 'agent-revit-orchestrator', 'data')
FAISS_INDEX_PATH = os.path.join(DATA_DIR, 'faiss_index.bin')
MAPPING_PATH = os.path.join(DATA_DIR, 'index_to_api.json')
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Cargamos los componentes del RAG al inicio
try:
    logger.info("Cargando componentes del RAG...")
    rag_index = faiss.read_index(FAISS_INDEX_PATH)
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        index_to_api_map = json.load(f)
    rag_model = SentenceTransformer(MODEL_NAME)
    RAG_ENABLED = True
    logger.info("✅ Componentes RAG cargados con éxito.")
except Exception as e:
    logger.error(f"ADVERTENCIA: No se pudieron cargar los archivos del RAG. El contexto de la API estará vacío. Error: {e}", exc_info=True)
    RAG_ENABLED = False

# --- 2. Lógica de Negocio (NLU, RAG, Prompting Mejorado) ---
def find_relevant_api_context(query: str, k: int = 4) -> list[str]:
    if not RAG_ENABLED:
        return []
    try:
        query_vector = rag_model.encode([query])
        _, indices = rag_index.search(np.array(query_vector).astype('float32'), k)
        return [index_to_api_map.get(str(i)) for i in indices[0] if str(i) in index_to_api_map]
    except Exception as e:
        logger.error(f"Error durante la búsqueda RAG para la consulta '{query}': {e}", exc_info=True)
        return []

def build_super_prompt(user_text: str, intent: str, slots: dict, revit_context: dict, previous_code: str = None, error_message: str = None) -> str:
    """
    Construye el prompt final, incluyendo el "System Prompt" y el contexto de depuración.
    """
    api_context = find_relevant_api_context(user_text)
    
    prompt = "### INSTRUCTION:\n"
    prompt += "You are an expert C# programmer for the Autodesk Revit API. Your task is to generate a C# code snippet that can be executed directly. Follow these rules:\n"
    prompt += "- Generate ONLY raw C# code. Do not include explanations, comments, or markdown formatting like ```csharp.\n"
    prompt += "- The code will have access to a pre-defined 'doc' object (the active Revit Document).\n"
    prompt += "- If you need to modify the Revit document, you MUST wrap your code in a Transaction. Example: using (Transaction t = new Transaction(doc, \"My Action\")) { t.Start(); /* your code */ t.Commit(); }\n"
    prompt += "- Use UnitUtils.ConvertToInternalUnits for any measurements.\n"
    
    prompt += f"\n--- User Request Details ---\n"
    prompt += f"- User Request: '{user_text}'\n"
    if intent != "Unknown":
        prompt += f"- Detected Intent: {intent}\n"
    if slots:
        prompt += f"- Extracted Parameters: {json.dumps(slots)}\n"
    if revit_context:
        prompt += f"- Active Revit Context: {json.dumps(revit_context)}\n"
    
    if api_context:
        prompt += "\n--- Relevant API Documentation (Context)---\n"
        for item in api_context:
            prompt += f"- {item}\n"
    
    if error_message and previous_code:
        prompt += "\n--- DEBUGGING CONTEXT ---\n"
        prompt += "The previously generated code failed with an error.\n"
        prompt += f"- Previous Code:\n{previous_code}\n"
        prompt += f"- Error Message: {error_message}\n"
        prompt += "Please provide a corrected version of the C# code snippet that fixes this error.\n"

    prompt += "--------------------------\n"
    prompt += "\n\n### RESPONSE:\n"
    return prompt

def call_coder_agent(prompt: str) -> dict:
    try:
        payload = {"prompt": prompt}
        response = requests.post(AGENT_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"No se pudo conectar con el agente de código en {AGENT_URL}. Detalles: {e}")
        return {"code": f"// ERROR: No se pudo conectar con el agente de código. Verifique que el contenedor 'revit-code' esté en funcionamiento.\n// {e}"}

# --- 3. Endpoints de la API ---

@app.route("/process_instruction", methods=["POST"])
def process_instruction():
    """
    Endpoint principal: recibe la primera petición del usuario.
    Realiza el NLU y el RAG para generar el primer intento de código.
    """
    try:
        data = request.json
        user_text = data.get("text", "").strip()
        revit_context = data.get("context", {})

        if not user_text:
            return jsonify({"error": "El campo 'text' no puede estar vacío."}), 400

        logger.info(f"--- INICIO DE NUEVA PETICIÓN: '{user_text}' ---")
        
        # FASE 1: NLU
        intent = classify_intent(user_text)
        slots = extract_slots(user_text, intent)
        logger.info(f"1. NLU -> Intención: [{intent}], Slots: {slots}")

        # FASE 2: RAG y Prompting (Primer intento)
        final_prompt = build_super_prompt(user_text, intent, slots, revit_context)
        logger.info(f"2. Prompt construido para el primer intento.")

        # FASE 3: Delegación al Coder
        coder_response = call_coder_agent(final_prompt)
        logger.info(f"3. Primer fragmento de código generado.")

        # FASE 4: Respuesta
        # Devolvemos todo el contexto para que el cliente (plugin de Revit) pueda usarlo si necesita reintentar.
        final_response = {
            "original_text": user_text,
            "revit_context": revit_context,
            "intent": intent,
            "slots": slots,
            "generated_code": coder_response.get("code", "")
        }
        return jsonify(final_response)
        
    except Exception as e:
        logger.error(f"Ha ocurrido un error inesperado en /process_instruction: {e}", exc_info=True)
        return jsonify({"error": f"Error interno en el orquestador: {str(e)}"}), 500


@app.route("/refine_code", methods=["POST"])
def refine_code():
    """
    Endpoint de refinamiento: el plugin de Revit llama a este endpoint
    SOLO si el código anterior falló al ejecutarse.
    """
    try:
        data = request.json
        # El cliente debe devolver toda la información de la petición original
        user_text = data.get("original_text", "").strip()
        revit_context = data.get("revit_context", {})
        intent = data.get("intent", "Unknown")
        slots = data.get("slots", {})
        previous_code = data.get("failed_code", "")
        error_message = data.get("error_message", "")

        if not user_text or not previous_code or not error_message:
            return jsonify({"error": "La petición de refinamiento debe incluir 'original_text', 'failed_code' y 'error_message'."}), 400
            
        logger.info(f"--- INICIO DE PETICIÓN DE REFINAMIENTO para: '{user_text}' ---")
        logger.warning(f"Error recibido de Revit: {error_message}")

        # FASE 1: Construir el prompt de depuración
        refinement_prompt = build_super_prompt(user_text, intent, slots, revit_context, previous_code, error_message)
        logger.info("1. Prompt de refinamiento construido.")
        
        # FASE 2: Delegar al Coder para obtener una versión corregida
        coder_response = call_coder_agent(refinement_prompt)
        logger.info("2. Código corregido recibido del Agente.")

        # FASE 3: Devolver el nuevo código
        final_response = {
            "original_text": user_text,
            "revit_context": revit_context,
            "intent": intent,
            "slots": slots,
            "generated_code": coder_response.get("code", "")
        }
        return jsonify(final_response)

    except Exception as e:
        logger.error(f"Ha ocurrido un error inesperado en /refine_code: {e}", exc_info=True)
        return jsonify({"error": f"Error interno en el orquestador: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)