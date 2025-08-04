import os
import torch
import functools
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

# --- 0. Carga de Token ---
load_dotenv()
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# --- 1. CONFIGURACIÓN ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

BASE_MODEL_NAME   = "meta-llama/CodeLlama-7b-instruct-hf"
# ¡ASEGÚRATE DE APUNTAR A TU DATASET FINAL CURADO!
DATA_PATH         = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data.jsonl") 
OUTPUT_DIR        = os.path.join(REPO_ROOT, "Revit-Agent", "training_artifacts", "lora_revit_agent_codellama_v3") # ¡Nueva versión!

# --- 2. PROCESAMIENTO DE DATOS (FORMATO NATIVO DE LLAMA INSTRUCT) ---

SYSTEM_PROMPT = "You are an expert C# programmer for the Autodesk Revit API. Your task is to generate a C# code snippet that can be executed directly to fulfill the user's request. Generate ONLY the raw C# code, without explanations, comments, or markdown formatting."

def create_and_tokenize_prompt(examples, tokenizer):
    """
    Crea el prompt en el formato nativo de Llama y lo tokeniza, enmascarando el prompt.
    """
    max_length = 1024
    
    # Extraemos las columnas del batch
    prompts = examples.get('prompt')
    completions = examples.get('completion')
    
    # Listas para guardar los resultados tokenizados
    model_inputs = {"input_ids": [], "attention_mask": [], "labels": []}

    for prompt, completion in zip(prompts, completions):
        # 1. Construir el prompt completo (instrucción + respuesta)
        full_text = f"<s>[INST] <<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n{prompt} [/INST]{completion} </s>"
        
        # 2. Tokenizar el texto completo
        tokenized_full = tokenizer(
            full_text,
            max_length=max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt"
        )
        
        # 3. Construir y tokenizar solo la parte del prompt (para enmascarar)
        prompt_only = f"<s>[INST] <<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n{prompt} [/INST]"
        tokenized_prompt = tokenizer(
            prompt_only,
            max_length=max_length,
            truncation=True,
            return_tensors="pt"
        )
        prompt_len = len(tokenized_prompt["input_ids"][0])
        
        # 4. Crear las etiquetas y enmascarar la parte del prompt
        labels = tokenized_full["input_ids"][0].clone()
        labels[:prompt_len] = -100 # El -100 es el valor estándar para ignorar en el cálculo del loss
        
        model_inputs["input_ids"].append(tokenized_full["input_ids"][0])
        model_inputs["attention_mask"].append(tokenized_full["attention_mask"][0])
        model_inputs["labels"].append(labels)
        
    return model_inputs

# --- FUNCIÓN PRINCIPAL DE ENTRENAMIENTO ---
if __name__ == '__main__':
    print(f"INFO: Iniciando re-entrenamiento con el modelo base: {BASE_MODEL_NAME}")
    print(f"INFO: Usando dataset de alta calidad: {DATA_PATH}")
    
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True, token=HF_TOKEN)
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

    # --- Carga y Procesamiento del Dataset ---
    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    
    tokenized_dataset = dataset.map(
        functools.partial(create_and_tokenize_prompt, tokenizer=tokenizer),
        batched=True,
        batch_size=10, # Usamos un batch size más pequeño para el pre-procesamiento
        remove_columns=dataset.column_names
    )
    
    split_dataset = tokenized_dataset.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split_dataset["train"], split_dataset["test"]
    print(f"INFO: Dataset listo. Entrenamiento: {len(train_ds)} | Evaluación: {len(eval_ds)}")

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    
    output_dir_name = os.path.basename(OUTPUT_DIR)

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3, # Empecemos con 3 épocas. Con datos de alta calidad, puede ser suficiente.
        learning_rate=1e-4,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",
        fp16=True,
        logging_dir=os.path.join(REPO_ROOT, "Revit-Agent", "training_artifacts", "logs", output_dir_name),
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        report_to="tensorboard",
        dataloader_pin_memory=False
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=data_collator,
        # No necesitamos pasar el tokenizer aquí si el data_collator ya lo tiene
    )

    print("\n" + "="*60)
    print("🚀  INICIANDO RE-ENTRENAMIENTO (FORMATO NATIVO LLAMA)  🚀")
    print("="*60 + "\n")
    
    trainer.train()

    print("\nINFO: Guardando el mejor adaptador LoRA...")
    trainer.save_model(OUTPUT_DIR)
    
    print("\n" + "🏆"*10)
    print(f"✅ ¡RE-ENTRENAMIENTO COMPLETADO! El nuevo modelo está en: '{OUTPUT_DIR}'")
    print("🏆"*10)