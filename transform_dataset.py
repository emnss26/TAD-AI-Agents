import os
import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# --- Configuración de Rutas ---
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SHARED_LIBS_PATH = os.path.join(REPO_ROOT, 'Shared-Libs')
sys.path.insert(0, SHARED_LIBS_PATH)

from nlu.intent_classifier import classify_intent
from nlu.slot_filler import extract_slots

# Rutas a los archivos de datos y del RAG
DATA_DIR = os.path.join(REPO_ROOT, 'Revit-Agent', 'agent-revit-orchestrator', 'data')
IN_FILE = os.path.join(DATA_DIR, 'train_data.jsonl')
OUT_FILE = os.path.join(DATA_DIR, 'train_data_rag_format_v2.jsonl') # Nuevo nombre de archivo
FAISS_INDEX_PATH = os.path.join(DATA_DIR, 'faiss_index.bin')
MAPPING_PATH = os.path.join(DATA_DIR, 'index_to_api.json')

# --- Cargamos los componentes del RAG al inicio ---
print("INFO: Cargando componentes del RAG...")
try:
    rag_index = faiss.read_index(FAISS_INDEX_PATH)
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        index_to_api_map = json.load(f)
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    RAG_ENABLED = True
    print("INFO: RAG cargado con éxito.")
except FileNotFoundError:
    print("ADVERTENCIA: No se encontraron los archivos del RAG. 'RELEVANT_API_CONTEXT' estará vacío.")
    RAG_ENABLED = False


def find_relevant_api_context(query: str, k: int = 3) -> list[str]:
    """
    Busca en el índice FAISS los k fragmentos de API más relevantes para la consulta.
    """
    if not RAG_ENABLED:
        return []
    
    query_vector = model.encode([query])
    distances, indices = rag_index.search(np.array(query_vector).astype('float32'), k)
    
    # El mapeo usa claves string, así que convertimos los índices
    return [index_to_api_map.get(str(i), "Unknown API entry") for i in indices[0]]


def transform():
    """
    Transforma el dataset original al nuevo formato RAG, incluyendo el contexto de la API.
    """
    print(f"Transformando {IN_FILE} -> {OUT_FILE}...")
    with open(IN_FILE, 'r', encoding='utf-8') as fin, \
         open(OUT_FILE, 'w', encoding='utf-8') as fout:

        for i, line in enumerate(fin):
            try:
                obj = json.loads(line)
                user_request = (obj.get('prompt') or "").split('\n')[0]
                completion = obj.get('completion', '')
                
                if not user_request or not completion:
                    continue

                # 1. NLU
                intent = classify_intent(user_request)
                slots = extract_slots(user_request, intent)

                # 2. RAG (Retrieval)
                api_context = find_relevant_api_context(user_request)

                # 3. Construcción del nuevo objeto
                new_obj = {
                    "USER_REQUEST": user_request,
                    "DETECTED_INTENT": intent,
                    "EXTRACTED_SLOTS": slots,
                    "RELEVANT_API_CONTEXT": api_context,
                    "EXPECTED_COMPLETION": completion # Guardamos el código esperado
                }
                fout.write(json.dumps(new_obj, ensure_ascii=False) + "\n")

                if i % 500 == 0:
                    print(f"  Procesadas {i} líneas...")

            except json.JSONDecodeError:
                print(f"Advertencia: Se omitió una línea mal formada: {line.strip()}")
                continue
    
    print("\n✅ ¡Dataset transformado con formato RAG completo!")


if __name__ == "__main__":
    transform()