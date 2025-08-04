import os
import json

# --- CONFIGURACIÓN DE RUTAS FIJAS ---
# Asume que este script está en Revit-Agent/scripts, y sube un nivel a Revit-Agent
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Directorio donde vive agent-revit-coder/data
DATA_DIR = os.path.join(BASE_DIR, 'agent-revit-coder', 'data')
# Entrada: carpeta o archivo .jsonl con los pares prompt/completion
INPUT_DIR = os.path.join(DATA_DIR, 'base_train_data')
# Salida: JSONL ya en formato meta-llama instruct
OUTPUT_FILE = os.path.join(DATA_DIR, 'train_data_llama.jsonl')

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
    """
    Recorre todos los JSONL en input_path (archivo o carpeta) y escribe
    un único JSONL en formato meta-llama instruct en output_file.
    """
    with open(output_file, 'w', encoding='utf-8') as fout:
        # Recolecta todos los .jsonl
        files = []
        if os.path.isdir(input_path):
            for fname in sorted(os.listdir(input_path)):
                if fname.lower().endswith('.jsonl'):
                    files.append(os.path.join(input_path, fname))
        else:
            files = [input_path]

        for path in files:
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
                        json_line = json.dumps({'text': inst}, ensure_ascii=False)
                        fout.write(json_line + '\n')
                    except json.JSONDecodeError:
                        # Línea corrupta: la saltamos
                        continue


if __name__ == '__main__':
    print(f"Convirtiendo datos de '{INPUT_DIR}' a '{OUTPUT_FILE}'...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    convert_jsonl(INPUT_DIR, OUTPUT_FILE)
    print("Conversión completada.")