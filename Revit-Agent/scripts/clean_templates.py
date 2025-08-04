import json
import re
import os

def clean_jsonl_file(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"❌ Error: El archivo de entrada no se encontró en la ruta esperada:\n   '{input_path}'")
        return

    corrected_lines = []
    print(f"Iniciando la limpieza del archivo: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f_in:
        for i, line in enumerate(f_in, 1):
            if not line.strip(): continue
            
            try:
                data = json.loads(line)
                if 'completion_template' in data and data['completion_template']:
                    placeholders = set(re.findall(r'\{(\w+)\}', data['completion_template']))
                    data['vars_needed'] = sorted(list(placeholders))
                corrected_lines.append(json.dumps(data, ensure_ascii=False))
            except json.JSONDecodeError:
                print(f"Línea {i}: Omitiendo línea mal formada: {line.strip()}")

    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    with open(output_path, 'w', encoding='utf-8') as f_out:
        for line in corrected_lines: f_out.write(line + '\n')

    print(f"\n✅ Limpieza completada. {len(corrected_lines)} plantillas procesadas.")
    print(f"   Archivo corregido guardado en: {output_path}")

# --- CONFIGURACIÓN AUTOMÁTICA DE RUTAS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)


# 3. Construye las rutas completas y seguras a los archivos de datos
INPUT_FILENAME = os.path.join(project_root, 'agent-revit-coder',  'data', 'base_training_template.jsonl')
CORRECTED_FILENAME = os.path.join(project_root, 'agent-revit-coder','data', 'templates_to_validate_corrected.jsonl')


# --- EJECUCIÓN ---
clean_jsonl_file(INPUT_FILENAME, CORRECTED_FILENAME)