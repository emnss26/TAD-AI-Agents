import os
import json
import sys

# --- CONFIGURACIÓN DE RUTAS FIJAS ---
# Partiendo de Revit-Agent/scripts/, subimos dos niveles a la raíz del repositorio
SCRIPT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
# Dentro de Revit-Agent: agent-revit-coder/data
DATA_DIR = os.path.join(BASE_DIR, 'Revit-Agent', 'agent-revit-coder', 'data')

# Entrada: puede ser un único .jsonl o un directorio con varios .jsonl
INPUT_PATH = os.path.join(DATA_DIR, 'base_training_template.jsonl')
# Salida: JSONL ya en formato meta-llama instruct
OUTPUT_FILE = os.path.join(DATA_DIR, 'train_data_llama_templates.jsonl')

SYSTEM_PROMPT = (
    "You are an expert C# programmer for the Autodesk Revit API. "
    "Your task is to generate a C# code snippet that can be executed directly "
    "to fulfill the user's request. Generate ONLY the raw C# code, without "
    "explanations, comments, or markdown formatting."
)

TEMPLATE = (
    "<s>[INST] <<SYS>>\n"
    "{system}\n"
    "<</SYS>>\n\n"
    "{prompt} [/INST]\n"
    "{completion}</s>"
)

def convert_jsonl(input_path, output_file):
    # 1) Recolectar archivos .jsonl
    if os.path.isdir(input_path):
        files = sorted(
            os.path.join(input_path, fn)
            for fn in os.listdir(input_path)
            if fn.lower().endswith('.jsonl')
        )
    else:
        files = [input_path]

    if not files:
        raise FileNotFoundError(f"No se encontró ningún .jsonl en '{input_path}'")

    # 2) Procesar y escribir
    with open(output_file, 'w', encoding='utf-8') as fout:
        for path in files:
            if not os.path.isfile(path):
                print(f"⚠️  Saltando (no existe): {path}", file=sys.stderr)
                continue

            with open(path, 'r', encoding='utf-8') as fin:
                for i, line in enumerate(fin, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        print(f"⚠️  Línea {i} en {path} no válida JSON, salteando.", file=sys.stderr)
                        continue

                    # admitir prompt/completion o prompt_template/completion_template
                    prompt = obj.get('prompt') or obj.get('prompt_template') or ""
                    completion = obj.get('completion') or obj.get('completion_template') or ""

                    prompt = prompt.strip()
                    completion = completion.rstrip()

                    if not prompt and not completion:
                        # nada que hacer
                        continue

                    inst = TEMPLATE.format(
                        system=SYSTEM_PROMPT,
                        prompt=prompt,
                        completion=completion
                    )
                    fout.write(json.dumps({'text': inst}, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    print(f"🔄 Convirtiendo '{INPUT_PATH}' → '{OUTPUT_FILE}'")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    try:
        convert_jsonl(INPUT_PATH, OUTPUT_FILE)
    except Exception as e:
        print("❌ Error:", e, file=sys.stderr)
        sys.exit(1)
    print("✅ Conversión completada.")