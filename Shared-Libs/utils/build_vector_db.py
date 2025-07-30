import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# --- Configuración de Rutas ---
# Nos aseguramos de que las rutas se construyan desde la raíz del proyecto
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
API_CATALOG_PATH = os.path.join(REPO_ROOT, 'Revit-Agent', 'agent-revit-orchestrator', 'data', 'revit_api_reflection.json')
OUTPUT_DIR = os.path.join(REPO_ROOT, 'Revit-Agent', 'agent-revit-orchestrator', 'data')
FAISS_INDEX_PATH = os.path.join(OUTPUT_DIR, 'faiss_index.bin')
MAPPING_PATH = os.path.join(OUTPUT_DIR, 'index_to_api.json')

# --- Modelo para crear los vectores ---
# 'all-MiniLM-L6-v2' es un modelo excelente: rápido, pequeño y muy efectivo para búsqueda semántica.
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

def build_vector_database():
    """
    Lee el JSON de la API de Revit, lo convierte en vectores y guarda un índice FAISS
    y un archivo de mapeo.
    """
    print("INFO: Cargando catálogo de la API de Revit...")
    try:
        with open(API_CATALOG_PATH, 'r', encoding='utf-8') as f:
            api_catalog = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: No se encontró el catálogo de la API en {API_CATALOG_PATH}")
        return

    # 1. Preparar los documentos de texto que vamos a vectorizar
    documents = []
    index_to_api_map = {}
    doc_index = 0
    for class_info in api_catalog:
        class_name = class_info.get("type", "UnknownClass")
        # Incluimos métodos
        for method in class_info.get("methods", []):
            # Creamos una descripción textual rica para cada método
            doc_text = f"Class: {class_name}. Method: {method.get('signature', '')}"
            documents.append(doc_text)
            index_to_api_map[doc_index] = doc_text
            doc_index += 1
        # Incluimos propiedades
        for prop in class_info.get("properties", []):
            doc_text = f"Class: {class_name}. Property: {prop}"
            documents.append(doc_text)
            index_to_api_map[doc_index] = doc_text
            doc_index += 1
            
    if not documents:
        print("ERROR: No se encontraron documentos para indexar en el catálogo de la API.")
        return

    print(f"INFO: Se prepararon {len(documents)} documentos de la API para ser vectorizados.")

    # 2. Cargar el modelo de embeddings
    print(f"INFO: Cargando el modelo de Sentence Transformer: '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    # 3. Crear los vectores (embeddings)
    print("INFO: Codificando documentos a vectores... (Esto puede tardar un poco la primera vez)")
    embeddings = model.encode(documents, show_progress_bar=True)
    embeddings = np.array(embeddings).astype('float32')
    
    # 4. Construir y entrenar el índice FAISS
    dimension = embeddings.shape[1]  # Dimensión de los vectores (ej. 384 para MiniLM)
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    print(f"INFO: Se ha construido un índice FAISS con {index.ntotal} vectores.")

    # 5. Guardar el índice y el mapeo
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"INFO: Índice FAISS guardado en: {FAISS_INDEX_PATH}")
    
    with open(MAPPING_PATH, 'w', encoding='utf-8') as f:
        json.dump(index_to_api_map, f, ensure_ascii=False, indent=2)
    print(f"INFO: Mapeo de contenido guardado en: {MAPPING_PATH}")
    
    print("\n✅ ¡Base de datos vectorial construida con éxito!")

if __name__ == "__main__":
    build_vector_database()