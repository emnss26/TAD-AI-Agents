# scripts/train_lora.py (Versión con caché forzada por variable de entorno)

import os
import torch
import functools
import json
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from dotenv import load_dotenv

# --- Carga del Token de Autenticación (se mantiene igual) ---
load_dotenv()
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
if not HF_TOKEN:
    print("ADVERTENCIA: No se encontró el token de Hugging Face en el archivo .env.")
# ----------------------------------------

# --- 1. DEFINICIÓN DE RUTAS Y MODELO ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

BASE_MODEL_NAME   = "meta-llama/CodeLlama-7b-instruct-hf"
DATA_PATH         = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-orchestrator", "data", "train_data_rag_format_v2.jsonl") 
OUTPUT_DIR        = os.path.join(REPO_ROOT, "lora_revit_agent_codellama_v1")
# Ya no necesitamos definir CACHE_DIR aquí, la variable de entorno lo manejará.

# --- 2. FUNCIONES DE PROCESAMIENTO DE DATOS (se mantienen igual) ---
def create_rag_prompt(example, tokenizer):
    # ... (esta función no cambia)
    user_request = example.get("USER_REQUEST", "")
    intent = example.get("DETECTED_INTENT", "Unknown")
    slots = example.get("EXTRACTED_SLOTS", {})
    api_context = example.get("RELEVANT_API_CONTEXT", [])
    completion = example.get("EXPECTED_COMPLETION", "")
    prompt = "### INSTRUCTION:\n"
    prompt += f"Based on the following user request and context, generate the C# code for the Revit API.\n"
    prompt += f"- User Request: '{user_request}'\n"
    if intent != "Unknown":
        prompt += f"- Detected Intent: {intent}\n"
    if slots:
        prompt += f"- Extracted Parameters: {slots}\n"
    if api_context:
        prompt += "\n--- Relevant API Documentation (Context)---\n"
        for item in api_context:
            prompt += f"- {item}\n"
        prompt += "--------------------------------------\n"
    prompt += "Generate ONLY the C# code snippet. Do not add explanations or surrounding text."
    prompt += "\n\n### RESPONSE:\n"
    full_text = prompt + completion + tokenizer.eos_token
    return full_text

def tokenize_dataset(tokenizer, batch):
    # ... (esta función no cambia)
    max_length = 1024 
    formatted_texts = [create_rag_prompt(example, tokenizer) for example in batch]
    tokenized = tokenizer(
        formatted_texts,
        truncation=True,
        max_length=max_length,
        padding="max_length"
    )
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

# --- FUNCIÓN PRINCIPAL DE ENTRENAMIENTO ---
if __name__ == '__main__':
    print(f"INFO: Iniciando entrenamiento con el modelo base: {BASE_MODEL_NAME}")
    
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # Ahora las librerías leerán la caché desde la variable de entorno HF_HOME
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_NAME, 
        trust_remote_code=True,
        token=HF_TOKEN
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_NAME,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
        token=HF_TOKEN
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print(f"INFO: Cargando y procesando dataset RAG desde {DATA_PATH}...")
    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    
    def map_function(batch):
        keys = batch.keys()
        list_of_dicts = [dict(zip(keys, values)) for values in zip(*batch.values())]
        return tokenize_dataset(tokenizer, list_of_dicts)

    tokenized_dataset = dataset.map(
        map_function,
        batched=True,
        batch_size=100,
        remove_columns=dataset.column_names
    )

    output_dir_name = os.path.basename(OUTPUT_DIR)
    
    split_dataset = tokenized_dataset.train_test_split(test_size=0.05, seed=42)
    train_ds, eval_ds = split_dataset["train"], split_dataset["test"]
    print(f"INFO: Dataset listo. Tamaño de entrenamiento: {len(train_ds)} | Tamaño de evaluación: {len(eval_ds)}")

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=1e-4,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",
        fp16=True, # Usamos fp16 por compatibilidad
        logging_dir=f"./logs/{output_dir_name}", # Ruta de logging corregida
        logging_steps=25,
        evaluation_strategy="epoch",
        save_strategy="epoch", 
        save_total_limit=2,
        load_best_model_at_end=True,
        report_to="tensorboard",
        dataloader_pin_memory=False # Añadido para evitar bloqueos en Windows
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=data_collator,
        tokenizer=tokenizer
    )

    print("\n" + "="*60)
    print("🚀  INICIANDO ENTRENAMIENTO DE ÉLITE CON CodeLlama y RAG  🚀")
    print("="*60 + "\n")
    
    trainer.train()

    print("\nINFO: Guardando el mejor adaptador LoRA...")
    trainer.save_model(OUTPUT_DIR)
    
    print("\n" + "🏆"*10)
    print(f"✅ ¡MISIÓN CUMPLIDA! El entrenamiento de nueva generación ha finalizado.")
    print(f"✅ El mejor modelo está guardado en: './{OUTPUT_DIR}'")
    print("🏆"*10)