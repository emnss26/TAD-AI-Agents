import os
import json
import re

def create_variable_inventory(input_path):
    """
    Lee un archivo .jsonl y extrae todos los placeholders únicos
    de los campos 'prompt_template' y 'completion_template'.
    """
    if not os.path.exists(input_path):
        print(f"❌ Error: El archivo de entrada no se encontró en: '{input_path}'")
        return

    all_variables = set()
    print(f"Iniciando inventario de variables desde: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
                
                # Extraer de ambos campos por seguridad
                prompt = data.get("prompt_template", "")
                completion = data.get("completion_template", "")
                
                variables_in_line = re.findall(r'\{(\w+)\}', prompt + completion)
                all_variables.update(variables_in_line)

            except json.JSONDecodeError:
                print(f"Línea {i}: Omitiendo línea mal formada: {line.strip()}")

    # Ordenar alfabéticamente para una fácil revisión
    sorted_variables = sorted(list(all_variables))

    print("\n" + "="*50)
    print("      INVENTARIO COMPLETO DE VARIABLES ENCONTRADAS")
    print("="*50)
    print(f"Total de variables únicas: {len(sorted_variables)}")
    print("-" * 50)
    
    # Imprimir en un formato fácil de copiar y pegar para el diccionario DATA_POOLS
    for var in sorted_variables:
        # Sugerir un tipo basado en el nombre de la variable
        if "name" in var or "comment" in var or "material" in var or "family" in var or "type" in var or "prefix" in var:
            print(f'    "{var}": ["Mock Value 1", "Mock Value 2"],')
        else:
            print(f'    "{var}": [1.0, 5.0, 10.5],')
            
    print("="*50)
    print("\n✅ Inventario completado. Revisa la lista de arriba y completa tu diccionario `DATA_POOLS` en el script `2_create_final_datasets.py`.")


# --- CONFIGURACIÓN ---
REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Asegúrate de apuntar al archivo correcto con todas las variantes semánticas
INPUT_FILE = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "templates_with_semantic_variants.jsonl")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    create_variable_inventory(INPUT_FILE)