import os
import json

# --- CONFIGURACIÓN DE RUTAS FIJAS ---
# Subimos DOS niveles desde scripts/ para llegar a .../Revit-Agent
SCRIPT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
# agent-revit-coder/data dentro de Revit-Agent
DATA_DIR = os.path.join(BASE_DIR, 'Revit-Agent', 'agent-revit-coder', 'data')

# Entrada: carpeta o archivo .jsonl con los pares prompt/completion
INPUT_PATH  = os.path.join(DATA_DIR, 'base_train_data.jsonl')
# Salida: JSONL en formato StarCoder2-Instruct
OUTPUT_FILE = os.path.join(DATA_DIR, 'train_data_starcoder.jsonl')

# ---------------------------------------------
# Nueva plantilla para StarCoder2-Instruct
TEMPLATE = (
    "### Instruction:\n"
    "{prompt}\n"
    "### Response:\n"
    "```csharp\n"
    "{completion}\n"
    "```\n"
    "### End"
)
# ---------------------------------------------

def convert_jsonl(input_path, output_file):
    """
    Recorre todos los JSONL en input_path (archivo o carpeta) y escribe
    un único JSONL en formato StarCoder2-Instruct en output_file.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    files = []
    if os.path.isdir(input_path):
        for fn in sorted(os.listdir(input_path)):
            if fn.lower().endswith('.jsonl'):
                files.append(os.path.join(input_path, fn))
    else:
        files = [input_path]

    if not files:
        raise FileNotFoundError(f"No se encontró ningún archivo .jsonl en '{input_path}'")

    with open(output_file, 'w', encoding='utf-8') as fout:
        for path in files:
            if not os.path.isfile(path):
                print(f"⚠️  Saltando (no existe): {path}")
                continue
            with open(path, 'r', encoding='utf-8') as fin:
                for line in fin:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        # línea inválida -> saltar
                        continue

                    prompt     = obj.get('prompt', '').strip()
                    completion = obj.get('completion', '').rstrip()
                    if not prompt or not completion:
                        # si falta uno de los dos, saltar
                        continue

                    wrapped = TEMPLATE.format(
                        prompt=prompt,
                        completion=completion
                    )
                    fout.write(json.dumps({'text': wrapped}, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    print(f"Convirtiendo '{INPUT_PATH}' → '{OUTPUT_FILE}'…")
    convert_jsonl(INPUT_PATH, OUTPUT_FILE)
    print("✅ Conversión a StarCoder2-Instruct completada.")