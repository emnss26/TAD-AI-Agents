import os
import json
import re
import random
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from dotenv import load_dotenv

def generate_variants(prompt, generator, num_variants=3):
    # MEJORA CLAVE: Un prompt de sistema mucho más específico para el dominio AEC
    system_prompt = (
        "You are an expert AI assistant for the Architecture, Engineering, and Construction (AEC) industry. "
        "Your task is to paraphrase technical instructions for Autodesk Revit software. "
        "The language must be professional, direct, and typical of an architect, engineer, or modeler. "
        "Do not use overly creative, poetic, or informal language. "
        "Crucially, DO NOT change the placeholders like {variable_name}.\n\n"
        "GOOD examples of professional language: 'Modelar un muro', 'Trazar una viga', 'Insertar una ventana', 'Ajustar la altura del antepecho', 'Create a floor plan', 'Set the parameter'.\n"
        "BAD examples of informal language: 'Erect a barrier', 'Fashion a window', 'Craft a structure', 'Draw up plans for a wall'.\n\n"
        "Respond ONLY with the list of paraphrased prompts, separated by newlines. Do not add numbering or explanations."
    )
    
    chat = [
        {"role": "user", "content": f"{system_prompt}\n\nOriginal instruction: \"{prompt}\"\n\nGenerate {num_variants} variations:"}
    ]
    
    formatted_prompt = generator.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    
    outputs = generator(
        formatted_prompt, 
        max_new_tokens=512, 
        num_return_sequences=1, 
        do_sample=True, 
        temperature=0.6, # Reducimos un poco la "creatividad"
        top_k=50, 
        top_p=0.95,
        eos_token_id=generator.tokenizer.eos_token_id
    )
    
    generated_text = outputs[0]["generated_text"]
    response = generated_text.split("[/INST]")[-1].strip()
    
    variants_raw = [v.strip() for v in response.split('\n') if v.strip() and '{' in v and '}' in v]
    
    # Limpiar numeración y comillas extra
    cleaned_variants = [re.sub(r'^\d+\.\s*', '', v).strip().strip('"') for v in variants_raw]
    
    return cleaned_variants

def main():
    # --- 1. CONFIGURACIÓN ---
    load_dotenv()
    HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

    GENERATOR_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
    NUM_VARIANTS_PER_TEMPLATE = 4 # MEJORA: Reducido a 4 por tu instrucción
    REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    INPUT_FILE = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "base_training_template.jsonl") 
    OUTPUT_FILE = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "templates_with_semantic_variants.jsonl")

    # --- 2. CARGA DEL MODELO ---
    print(f"Cargando el modelo generador: {GENERATOR_MODEL} en 4-bits...")
    os.environ["CUDA_VISIBLE_DEVICES"] = "0" 
    
    if torch.cuda.is_available():
        print(f"✅ Usando GPU para la generación: {torch.cuda.get_device_name(0)}")
    
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        GENERATOR_MODEL,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
        token=HF_TOKEN
    )
    tokenizer = AutoTokenizer.from_pretrained(GENERATOR_MODEL, token=HF_TOKEN)

    generator = pipeline("text-generation", model=model, tokenizer=tokenizer, torch_dtype=torch.bfloat16)
    print("✅ Modelo cargado.")

    # --- 3. PROCESAMIENTO DEL DATASET ---
    all_templates = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_templates.append(json.loads(line))

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for i, template in enumerate(all_templates):
            original_prompt = template.get("prompt_template", "")
            
            if not original_prompt: continue
            all_prompts = {original_prompt}
            
            print(f"[{i+1}/{len(all_templates)}] Generando variantes para: \"{original_prompt}\"")
            
            if '{' not in original_prompt:
                print("  -> Omitiendo, no es una plantilla parametrizada.")
            else:
                try:
                    # Generamos 3 nuevas variantes para un total de 4
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