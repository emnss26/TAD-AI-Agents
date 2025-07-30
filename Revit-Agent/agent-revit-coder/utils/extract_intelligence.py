import os
import json
import re
from tree_sitter import Language, Parser

# --- Configuración de Tree-sitter ---
# IMPORTANTE: Necesitas compilar la gramática de C# de Tree-sitter primero.
# Pasos para compilar la gramática (ejecutar en tu terminal):
# 1. Instala el binding de Python para tree-sitter: `pip install tree_sitter`
# 2. Instala la CLI de tree-sitter (si no la tienes): `npm install -g tree-sitter-cli`
# 3. Clona el repositorio de la gramática C#: `git clone https://github.com/tree-sitter/tree-sitter-csharp`
# 4. Compila la gramática: `tree-sitter build --output build/my-languages.so tree-sitter-csharp`
#    (Asegúrate de que el directorio 'build' exista, o cámbialo a tu preferencia)

GRAMMAR_PATH = './build/my-languages.so' # Ajusta esta ruta si es necesario
CSHARP_GRAMMAR_REPO = 'tree-sitter-csharp' # Nombre del directorio de la gramática clonada

# Verifica si la gramática compilada existe
if not os.path.exists(GRAMMAR_PATH):
    print(f"Error: Gramática de C# no encontrada en {GRAMMAR_PATH}.")
    print("Por favor, sigue los pasos de compilación indicados en el script.")
    exit(1) # Salir si la gramática no está lista

CSHARP_LANGUAGE = Language(GRAMMAR_PATH, 'c_sharp')
PARSER = Parser()
PARSER.set_language(CSHARP_LANGUAGE)

def get_node_text(node, source_code_bytes):
    """Extrae el texto original de un nodo del AST."""
    return source_code_bytes[node.start_byte:node.end_byte].decode('utf-8')

def get_indentation(line):
    """Calcula la cantidad de espacios en blanco al inicio de una línea."""
    return len(line) - len(line.lstrip())

def is_boilerplate_statement_line(line_content):
    """
    Determina si una línea de código es boilerplate basada en patrones heurísticos.
    Opera sobre el contenido de la línea sin comentarios finales.
    """
    trimmed_line = line_content.strip()
    if not trimmed_line:
        return False # Las líneas vacías no son boilerplate a descartar, solo de re-indentar.

    # Patrones de transacciones
    if re.search(r'\b(new\s+Transaction|Start\(\)|Commit\(\)|RollBack\(\)|Dispose\(\))\b', trimmed_line):
        return True

    # Patrones de UI
    if any(kw in trimmed_line for kw in ["TaskDialog.Show(", "System.Windows.Forms.", ".ShowDialog()", "MessageBox."]):
        return True

    # Retorno de comandos
    if trimmed_line.startswith("return Autodesk.Revit.UI.Result."):
        return True

    # Palabras clave de try-catch (aunque la lógica AST ya maneja los bloques completos)
    if trimmed_line.startswith("try {") or trimmed_line.startswith("catch (Exception"):
        return True
    
    # Comentarios de documentación XML (si se filtran línea por línea)
    if trimmed_line.startswith("///"):
        return True

    return False

def collect_core_logic_lines(node, source_code_bytes, collected_lines_with_indent):
    """
    Función recursiva para recolectar líneas de código relevantes, ignorando el boilerplate.
    Las líneas se almacenan con su indentación original.
    """
    if not node:
        return

    # Si es un bloque try, solo procesa el cuerpo del try.
    if node.type == 'try_statement':
        try_block = node.child_by_field_name('body')
        if try_block and try_block.type == 'block':
            collect_core_logic_lines(try_block, source_code_bytes, collected_lines_with_indent)
        return # No se añade el nodo 'try_statement' ni sus 'catch'/'finally'

    # Si es un bloque genérico o el programa raíz, procesa sus hijos.
    elif node.type == 'block' or node.type == 'program':
        for child in node.children:
            collect_core_logic_lines(child, source_code_bytes, collected_lines_with_indent)
        return

    # Para sentencias individuales, verifica si son boilerplate.
    node_full_text = get_node_text(node, source_code_bytes)
    lines = node_full_text.splitlines()

    for line in lines:
        if not line.strip(): # Mantener líneas vacías para formato
            collected_lines_with_indent.append(line)
            continue

        # Eliminar comentarios de una sola línea al final para la verificación de boilerplate
        line_content_no_comments = line.split('//')[0]

        if not is_boilerplate_statement_line(line_content_no_comments):
            collected_lines_with_indent.append(line)
        

def process_csharp_file(file_path, base_path_for_prompt=""):
    """
    Procesa un archivo C# para extraer la lógica central de Revit API.
    Genera un prompt descriptivo y una completion limpia.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            csharp_code = f.read()
    except Exception:
        # print(f"Error leyendo {file_path}: {e}") # Descomentar para depuración
        return None

    tree = PARSER.parse(bytes(csharp_code, 'utf-8'))
    root_node = tree.root_node
    source_code_bytes = bytes(csharp_code, 'utf-8')

    # Generación del prompt (ruta relativa por defecto)
    relative_path = os.path.relpath(file_path, base_path_for_prompt) if base_path_for_prompt else file_path
    prompt_text = f"Extract core Revit API logic from `{relative_path}`"
    
    collected_raw_lines = []
    found_execute_method = False

    # 1. Encontrar la clase que implementa IExternalCommand
    for node in root_node.children:
        if node.type == 'class_declaration':
            class_text = get_node_text(node, source_code_bytes)
            if "IExternalCommand" in class_text: # Heurística: la clase de comando
                # 2. Encontrar el método Execute
                for member in node.children_by_field_name('members'):
                    if member.type == 'method_declaration':
                        method_name_node = member.child_by_field_name('name')
                        if method_name_node and get_node_text(method_name_node, source_code_bytes) == 'Execute':
                            found_execute_method = True
                            
                            # 3. Intentar extraer el prompt de la documentación XML del método Execute
                            for sibling in member.prev_siblings:
                                if sibling.type == 'comment' and get_node_text(sibling, source_code_bytes).strip().startswith('///'):
                                    summary_match = re.search(r'<summary>(.*?)</summary>', get_node_text(sibling, source_code_bytes), re.DOTALL)
                                    if summary_match:
                                        extracted_summary = summary_match.group(1)
                                        clean_summary_lines = []
                                        for s_line in extracted_summary.splitlines():
                                            cleaned_s_line = s_line.replace('///', '').strip()
                                            if cleaned_s_line:
                                                clean_summary_lines.append(cleaned_s_line)
                                        
                                        final_summary = " ".join(clean_summary_lines).strip()
                                        
                                        # Usar el summary solo si es lo suficientemente específico
                                        if final_summary and not any(kw in final_summary.lower() for kw in ["implements the revit", "implement this method", "interface", "an external command"]):
                                            prompt_text = final_summary
                                            break # Usar este summary y detener la búsqueda
                            
                            # 4. Recolectar la lógica central del cuerpo del método Execute
                            method_body = member.child_by_field_name('body')
                            if method_body and method_body.type == 'block':
                                collect_core_logic_lines(method_body, source_code_bytes, collected_raw_lines)
                            break # Método Execute encontrado y procesado

                if found_execute_method:
                    break # Clase IExternalCommand encontrada y procesada

    if not collected_raw_lines:
        return None # No se encontró lógica relevante en el método Execute

    # 5. Post-procesamiento: Normalizar la indentación y limpieza final
    cleaned_final_lines = []
    min_indent = float('inf')

    # Calcular la indentación mínima de las líneas no vacías
    for line in collected_raw_lines:
        if line.strip():
            indent = get_indentation(line)
            min_indent = min(min_indent, indent)
    
    # Si no se encontraron líneas no vacías (ej. solo comentarios o boilerplate), establecer min_indent a 0
    if min_indent == float('inf'):
        min_indent = 0

    for line in collected_raw_lines:
        if line.strip():
            # Aplicar la de-indentación
            if get_indentation(line) >= min_indent:
                de_indented_line = line[min_indent:]
            else: # Esto no debería ocurrir si min_indent se calcula correctamente
                de_indented_line = line.strip()
            
            # Eliminar comentarios de una sola línea al final
            de_indented_line_no_comments = de_indented_line.split('//')[0].strip()
            
            # Eliminar comentarios de múltiples líneas (si no fueron capturados por el AST)
            de_indented_line_no_comments = re.sub(r'/\*.*?\*/', '', de_indented_line_no_comments, flags=re.DOTALL)
            
            if de_indented_line_no_comments:
                cleaned_final_lines.append(de_indented_line_no_comments)
        else:
            cleaned_final_lines.append("") # Preservar líneas en blanco

    final_completion = "\n".join(cleaned_final_lines).strip()
    
    # Asegurar una nueva línea al final para consistencia
    if final_completion and not final_completion.endswith('\n'):
        final_completion += '\n'

    return {"prompt": prompt_text, "completion": final_completion}

def process_sdk_samples(sdk_root_path, output_jsonl_path):
    """
    Recorre el directorio RevitSdkSamples, procesa los archivos C# y guarda el dataset.
    """
    dataset = []
    count_processed = 0
    count_skipped = 0

    # Asegúrate de que la ruta exista
    if not os.path.isdir(sdk_root_path):
        print(f"Error: El directorio '{sdk_root_path}' no existe.")
        return

    for root, _, files in os.walk(sdk_root_path):
        for file in files:
            if file.endswith('.cs'):
                full_path = os.path.join(root, file)
                
                # Para simplificar y enfocarse en los comandos ejecutables,
                # procesamos solo archivos llamados 'Command.cs' que típicamente
                # contienen la implementación de IExternalCommand.
                if "Command.cs" not in file:
                     continue 

                # print(f"Procesando: {full_path}") # Descomentar para ver el progreso
                result = process_csharp_file(full_path, sdk_root_path)
                if result:
                    dataset.append(result)
                    count_processed += 1
                else:
                    count_skipped += 1
                    # print(f"Saltado (no se encontró lógica relevante o es boilerplate): {full_path}") # Descomentar para ver saltados

    with open(output_jsonl_path, 'w', encoding='utf-8') as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"\nProcesamiento finalizado. Total procesados: {count_processed}, Total saltados: {count_skipped}")
    print(f"Dataset guardado en: {output_jsonl_path}")

# --- Ejemplo de Uso (Descomenta y ajusta las rutas para ejecutar) ---
# if __name__ == "__main__":
#     # Asegúrate de reemplazar esta ruta con la ubicación de tu clon de RevitSdkSamples
#     # Ejemplo: C:/Users/TuUsuario/Documents/GitHub/RevitSdkSamples
#     revit_sdk_samples_path = "ruta/a/tu/jeremytammik/RevitSdkSamples" 
#     output_dataset_path = "sdk_finetune_limpio.jsonl"
    
#     # Descomenta la siguiente línea para ejecutar el procesamiento
#     # process_sdk_samples(revit_sdk_samples_path, output_dataset_path)

#     # Ejemplo de cómo podrías probar un único archivo:
#     # test_file = "ruta/a/tu/jeremytammik/RevitSdkSamples/AddSpaceAndZone/CS/Command.cs"
#     # if os.path.exists(test_file):
#     #     test_result = process_csharp_file(test_file, os.path.dirname(os.path.dirname(os.path.dirname(test_file))))
#     #     if test_result:
#     #         print("\n--- Resultado de prueba para un solo archivo ---")
#     #         print(json.dumps(test_result, indent=2, ensure_ascii=False))
#     #     else:
#     #         print(f"\nNo se pudo extraer lógica del archivo de prueba: {test_file}")
#     # else:
#     #     print(f"\nArchivo de prueba no encontrado: {test_file}")