import json
import os

def format_for_mistral(input_path, output_path):
    """
    Convierte un dataset de prompt/completion al formato de chat de Mistral-Instruct.
    """
    if not os.path.exists(input_path):
        print(f"❌ Error: El archivo de entrada no se encontró en: '{input_path}'")
        return

    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        count = 0
        for line in f_in:
            if not line.strip():
                continue
            
            original_data = json.loads(line)
            
            # Asumimos que la entrada tiene 'prompt_template' y 'completion_template'
            # y los hemos limpiado para tener variables reales.
            prompt = original_data.get("prompt", "")
            completion = original_data.get("completion", "")

            if not prompt or not completion:
                continue

            # Construir el formato de Mistral
            # <s>[INST] Instrucción [/INST]Respuesta</s>
            mistral_formatted_text = f"<s>[INST] {prompt} [/INST]{completion}</s>"
            
            new_record = {"text": mistral_formatted_text}
            f_out.write(json.dumps(new_record, ensure_ascii=False) + '\n')
            count += 1

    print(f"✅ Conversión a formato Mistral completada.")
    print(f"   {count} registros procesados.")
    print(f"   Archivo nuevo guardado en: {output_path}")

# --- Configuración ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Usamos el archivo que ya limpiamos con el script anterior
INPUT_FILENAME = os.path.join(project_root, 'agent-revit-coder','data', 'base_train_data.jsonl')
OUTPUT_FILENAME = os.path.join(project_root, 'agent-revit-coder','data', 'train_data_mistral.jsonl')

# --- Ejecución ---
format_for_mistral(INPUT_FILENAME, OUTPUT_FILENAME)