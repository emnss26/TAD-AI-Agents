import os
import json
from bs4 import BeautifulSoup
import re
from tqdm import tqdm # Para una bonita barra de progreso

def clean_text(text):
    """Limpia el texto de espacios extra y saltos de línea."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text, max_length=1000):
    """Divide el texto en trozos más pequeños, respetando los párrafos."""
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(current_chunk) + len(p) + 1 < max_length:
            current_chunk += p + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def parse_html_file(file_path):
    """Parsea un único archivo HTML y extrae la información relevante."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f, 'lxml')

    # 1. Obtener el título
    title_tag = soup.find('title')
    if not title_tag:
        return None
    title = clean_text(title_tag.get_text())

    # 2. Obtener el contenido principal
    main_body = soup.find('div', id='mainBody')
    if not main_body:
        return None

    # Extraer y limpiar todo el texto visible
    content_text = clean_text(main_body.get_text(separator='\n', strip=True))
    
    return {"title": title, "content": content_text}


def main():
    # --- CONFIGURACIÓN ---
    html_directory = "../../../../Downloads/revit-api-chms-main/html/2024/html"   # Carpeta con los archivos .htm/.html
    output_file = "../../TAD-AI-Agents/agent-revit/revit_api_reference_dataset.jsonl"
    
    if not os.path.isdir(html_directory):
        print(f"Error: El directorio '{html_directory}' no existe. Por favor, crea la carpeta y descomprime ahí los archivos del CHM.")
        return

    all_files = [os.path.join(html_directory, f) for f in os.listdir(html_directory) if f.endswith(('.htm', '.html'))]
    
    print(f"Encontrados {len(all_files)} archivos HTML para procesar.")

    with open(output_file, 'w', encoding='utf-8') as f:
        # Usamos tqdm para una barra de progreso
        for file_path in tqdm(all_files, desc="Procesando archivos HTML"):
            parsed_data = parse_html_file(file_path)
            
            if parsed_data:
                # 3. Fragmentar el contenido
                text_chunks = chunk_text(parsed_data["content"])
                
                for chunk in text_chunks:
                    # 4. Crear el prompt y el completion
                    prompt = f"### Referencia API Revit: {parsed_data['title']}\n### Descripción:"
                    completion = chunk
                    
                    # 5. Escribir en el archivo JSONL
                    json_line = json.dumps({"prompt": prompt, "completion": completion}, ensure_ascii=False)
                    f.write(json_line + '\n')

    print(f"\n✅ ¡Proceso completado! Se ha creado el archivo '{output_file}'.")
    print(f"Puedes usar este archivo para RAG o para un fine-tuning de conocimiento.")

if __name__ == '__main__':
    main()