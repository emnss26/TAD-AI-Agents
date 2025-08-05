import os
import json

# --- CONFIGURACIÓN DE RUTAS FIJAS ---
# Ahora subimos DOS niveles desde scripts/ para llegar a .../Revit-Agent
SCRIPT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
# agent-revit-coder/data dentro de Revit-Agent
DATA_DIR = os.path.join(BASE_DIR, 'Revit-Agent','agent-revit-coder', 'data')

INPUT_DIR = os.path.join(DATA_DIR, 'base_train_data.jsonl')       # carpeta o archivo .jsonl de entrada
OUTPUT_FILE = os.path.join(DATA_DIR, 'train_data_llama.jsonl')  # archivo de salida

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
    "{completion}\n"
    "### END\n"
    "</s>"
)


def convert_jsonl(input_path, output_file):
    """
    Recorre todos los JSONL en input_path (archivo o carpeta) y escribe
    un único JSONL en formato meta-llama instruct en output_file.
    """
    with open(output_file, 'w', encoding='utf-8') as fout:
        # Recolecta todos los .jsonl
        if os.path.isdir(input_path):
            files = [
                os.path.join(input_path, fn)
                for fn in sorted(os.listdir(input_path))
                if fn.lower().endswith('.jsonl')
            ]
        else:
            files = [input_path]

        if not files:
            raise FileNotFoundError(f"No se encontró ningún archivo .jsonl en '{input_path}'")

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
                        prompt = obj.get('prompt', '').strip()
                        completion = obj.get('completion', '').rstrip()
                        inst = TEMPLATE.format(
                            system=SYSTEM_PROMPT,
                            prompt=prompt,
                            completion=completion
                        )
                        fout.write(json.dumps({'text': inst}, ensure_ascii=False) + '\n')
                    except json.JSONDecodeError:
                        # Línea corrupta: la saltamos
                        continue


if __name__ == '__main__':
    print(f"Convirtiendo datos de '{INPUT_DIR}' a '{OUTPUT_FILE}'...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    convert_jsonl(INPUT_DIR, OUTPUT_FILE)
    print("✅ Conversión completada.")