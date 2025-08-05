import os
import json
import random
import torch  # <-- ESTA ES LA LÍNEA MÁS IMPORTANTE
from transformers import pipeline
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
load_dotenv()
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# Modelo para generar las variantes. Usamos el mismo Mistral base, es excelente para esto.
GENERATOR_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
NUM_VARIANTS_PER_TEMPLATE = 12 # Generaremos ~10,200 ejemplos (850 * 12)
REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Asegúrate de que el nombre del archivo de entrada sea el correcto
INPUT_FILE = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "base_training_template.jsonl") 
OUTPUT_FILE = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "templates_with_semantic_variants.jsonl")

# --- LÓGICA ---
def generate_variants(prompt, generator, num_variants=5):
    system_prompt = "You are an expert in paraphrasing technical instructions for software. Generate multiple, distinct ways of asking for the same thing. Do not change the placeholders like {variable_name}. Respond ONLY with the list of paraphrased prompts, separated by newlines. Do not add numbering or explanations."
    
    chat = [
        {"role": "user", "content": f"{system_prompt}\n\nOriginal instruction: \"{prompt}\"\n\nGenerate {num_variants} variations:"}
    ]
    
    formatted_prompt = generator.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    outputs = generator(formatted_prompt, max_new_tokens=512, num_return_sequences=1, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
    
    generated_text = outputs[0]["generated_text"]
    response = generated_text.split("[/INST]")[-1].strip()
    
    # Filtro de calidad para asegurar que las variantes son útiles
    variants = [v.strip() for v in response.split('\n') if v.strip() and '{' in v and '}' in v]
    return variants

def main():
    print(f"Cargando el modelo generador: {GENERATOR_MODEL}...")
    # Forzar el uso de la GPU 0 (que para PyTorch es la RTX 4060)
    os.environ["CUDA_VISIBLE_DEVICES"] = "0" 
    
    # Verificar que estamos en la GPU correcta
    if torch.cuda.is_available():
        print(f"✅ Usando GPU para la generación: {torch.cuda.get_device_name(0)}")
    
    generator = pipeline("text-generation", model=GENERATOR_MODEL, device=0, token=HF_TOKEN, torch_dtype=torch.bfloat16)
    print("✅ Modelo cargado.")

    all_templates = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            all_templates.append(json.loads(line))

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for i, template in enumerate(all_templates):
            original_prompt = template["prompt_template"]
            
            all_prompts = {original_prompt}
            
            print(f"[{i+1}/{len(all_templates)}] Generando variantes para: \"{original_prompt}\"")
            
            # No generar variantes para prompts vacíos o sin placeholders
            if not original_prompt or '{' not in original_prompt:
                print("  -> Omitiendo, no es una plantilla parametrizada.")
            else:
                try:
                    variants = generate_variants(original_prompt, generator, num_variants=NUM_VARIANTS_PER_TEMPLATE - 1)
                    all_prompts.update(variants)
                except Exception as e:
                    print(f"  ⚠️ Error generando variantes: {e}. Usando solo el original.")

            for p in all_prompts:
                new_record = {
                    "prompt_template": p,
                    "completion_template": template["completion_template"],
                    "vars_needed": template["vars_needed"]
                }
                f_out.write(json.dumps(new_record, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Proceso completado. Archivo con variantes semánticas guardado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()