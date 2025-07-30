import os
import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# --- Configuración de Rutas ---
# El script se ejecuta desde la raíz, por lo que podemos construir rutas relativas simples.
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Añadimos la raíz del proyecto al path para poder importar el paquete 'shared_libs'
sys.path.insert(0, REPO_ROOT)

from shared_libs.nlu.intent_classifier import classify_intent
from shared_libs.nlu.slot_filler import extract_slots

# Rutas a los archivos de datos y del RAG
DATA_DIR = os.path.join(REPO_ROOT, 'Revit-Agent', 'agent-revit-orchestrator', 'data')
IN_FILE = os.path.join(DATA_DIR, 'train_data.jsonl')
OUT_FILE = os.path.join(DATA_DIR, 'train_data_rag_format_v2.jsonl')
FAISS_INDEX_PATH = os.path.join(DATA_DIR, 'faiss_index.bin')
MAPPING_PATH = os.path.join(DATA_DIR, 'index_to_api.json')
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# --- Cargamos los componentes del RAG al inicio ---
print("INFO: Cargando componentes del RAG...")
try:
    rag_index = faiss.read_index(FAISS_INDEX_PATH)
    with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
        # Las claves en JSON siempre son strings, así que cargamos tal cual.
        index_to_api_map = json.load(f)
    model = SentenceTransformer(MODEL_NAME)
    RAG_ENABLED = True
    print("INFO: RAG cargado con éxito.")
except Exception as e:
    print(f"ADVERTENCIA: No se pudieron cargar los archivos del RAG. 'RELEVANT_API_CONTEXT' estará vacío. Error: {e}")
    RAG_ENABLED = False


def find_relevant_api_context(query: str, k: int = 3) -> list[str]:
    """
    Busca en el índice FAISS los k fragmentos de API más relevantes para la consulta.
    """
    if not RAG_ENABLED:
        return []
    
    try:
        query_vector = model.encode([query])
        distances, indices = rag_index.search(np.array(query_vector).astype('float32'), k)
        
        # El mapeo usa claves string '0', '1', etc., así que convertimos los índices a string para buscar.
        return [index_to_api_map.get(str(i), "Unknown API entry") for i in indices[0]]
    except Exception as e:
        print(f"ERROR durante la búsqueda RAG para la consulta '{query}': {e}")
        return []


def transform():
    """
    Transforma el dataset original al nuevo formato RAG, incluyendo el contexto de la API.
    """
    print(f"Transformando {IN_FILE} -> {OUT_FILE}...")
    count = 0
    with open(IN_FILE, 'r', encoding='utf-8') as fin, \
         open(OUT_FILE, 'w', encoding='utf-8') as fout:

        for i, line in enumerate(fin):
            try:
                obj = json.loads(line)
                user_request = (obj.get('prompt') or "").strip()
                completion = obj.get('completion', '').strip()
                
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
                    "EXPECTED_COMPLETION": completion
                }
                fout.write(json.dumps(new_obj, ensure_ascii=False) + "\n")
                count += 1

                if (i + 1) % 500 == 0:
                    print(f"  Procesadas {i+1} líneas...")

            except json.JSONDecodeError:
                print(f"Advertencia: Se omitió una línea mal formada: {line.strip()}")
                continue
    
    print(f"\n✅ ¡Dataset transformado con formato RAG completo! Se procesaron {count} líneas.")


if __name__ == "__main__":
    transform()