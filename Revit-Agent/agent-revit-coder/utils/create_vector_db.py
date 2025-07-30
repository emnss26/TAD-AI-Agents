import os
import json
import re
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

def main():
    # --- CONFIGURACIÓN ---
    RAG_FOLDER = "rag_database"
    INPUT_JSONL_FILE = os.path.join(RAG_FOLDER, "revit_api_reference_dataset.jsonl")
    OUTPUT_TEXTS_FILE = os.path.join(RAG_FOLDER, "revit_api_texts_with_metadata.json")
    OUTPUT_INDEX_FILE = os.path.join(RAG_FOLDER, "revit_api.index")
    
    # Verificar que el archivo de entrada existe
    if not os.path.exists(INPUT_JSONL_FILE):
        print(f"Error: No se encontró el archivo '{INPUT_JSONL_FILE}'.")
        print("Asegúrate de haber creado la carpeta 'rag_database' y haber movido tu archivo .jsonl dentro.")
        return

    # --- 1. Cargar y procesar el dataset ---
    print(f"Leyendo y procesando '{INPUT_JSONL_FILE}'...")
    docs_with_metadata = []
    with open(INPUT_JSONL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                # Extraer el título del prompt, limpiando el formato
                title = data.get("prompt", "")
                title = re.sub(r'###\s*Referencia API Revit:\s*', '', title)
                title = re.sub(r'\s*###\s*Descripción:\s*', '', title).strip()
                
                content = data.get("completion", "")
                
                if title and content:
                    docs_with_metadata.append({"title": title, "content": content})
            except json.JSONDecodeError:
                print(f"Advertencia: Se omitió una línea mal formada en {INPUT_JSONL_FILE}")

    print(f"Procesados {len(docs_with_metadata)} documentos con título y contenido.")
    if not docs_with_metadata:
        print("No se encontraron documentos válidos para procesar. Abortando.")
        return

    # --- 2. Crear los Embeddings ---
    print("Cargando modelo de embeddings 'all-MiniLM-L6-v2' (puede tardar un momento)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print("Creando embeddings del contenido (esto puede tardar varios minutos)...")
    content_to_embed = [doc["content"] for doc in docs_with_metadata]
    embeddings = model.encode(content_to_embed, show_progress_bar=True, batch_size=128)
    embeddings = np.array(embeddings).astype('float32')

    # --- 3. Construir y guardar el índice FAISS ---
    print("Construyendo el índice FAISS...")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    print(f"Guardando índice en '{OUTPUT_INDEX_FILE}'...")
    faiss.write_index(index, OUTPUT_INDEX_FILE)
    
    print(f"Guardando textos y metadatos en '{OUTPUT_TEXTS_FILE}'...")
    with open(OUTPUT_TEXTS_FILE, "w", encoding='utf-8') as f:
        json.dump(docs_with_metadata, f, ensure_ascii=False, indent=4)

    print("\n✅ ¡Base de datos vectorial creada con éxito!")

if __name__ == '__main__':
    main()