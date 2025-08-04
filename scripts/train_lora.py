import os
import torch
import functools
from datasets import load_dataset, Dataset
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
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

BASE_MODEL_NAME   = "meta-llama/CodeLlama-7b-instruct-hf"
# ¡APUNTAMOS AL DATASET DE PLANTILLAS DE ALTA CALIDAD!
DATA_PATH         = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data.jsonl")
OUTPUT_DIR        = os.path.join(REPO_ROOT, "Revit-Agent", "training_artifacts", "lora_revit_agent_codellama_v3") # Nueva versión del modelo

# --- 2. PROCESAMIENTO DE DATOS (Estilo phi-2, simple y directo) ---
def format_prompt(example, tokenizer):
    """
    Crea el prompt en el formato simple que sabemos que funciona.
    """
    # Usamos los nombres de columna de tu 'base_train_data.jsonl'
    prompt_text = example.get('prompt_template') or example.get('prompt')
    completion_text = example.get('completion_template') or example.get('completion')

    return f"### INSTRUCTION:\n{prompt_text}\n\n### RESPONSE:\n{completion_text}{tokenizer.eos_token}"

def tokenize_dataset(tokenizer, examples):
    """
    Tokeniza un batch de ejemplos.
    """
    max_length = 1024 # Damos más espacio para el código complejo
    
    # El 'examples' que viene de .map es un diccionario de listas
    prompts = examples.get('prompt_template') or examples.get('prompt')
    completions = examples.get('completion_template') or examples.get('completion')

    formatted_texts = [
        f"### INSTRUCTION:\n{p}\n\n### RESPONSE:\n{c}{tokenizer.eos_token}"
        for p, c in zip(prompts, completions)
    ]

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
    print(f"INFO: Iniciando re-entrenamiento con el modelo base: {BASE_MODEL_NAME}")
    print(f"INFO: Usando dataset de plantillas: {DATA_PATH}")
    
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

    # --- Carga y Procesamiento del Dataset de Plantillas ---
    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    
    # Renombramos las columnas si es necesario para consistencia
    if "prompt_template" in dataset.column_names:
        dataset = dataset.rename_column("prompt_template", "prompt")
    if "completion_template" in dataset.column_names:
        dataset = dataset.rename_column("completion_template", "completion")

    tokenized_dataset = dataset.map(
        functools.partial(tokenize_dataset, tokenizer),
        batched=True,
        batch_size=100,
        remove_columns=dataset.column_names
    )
    
    split_dataset = tokenized_dataset.train_test_split(test_size=0.1, seed=42) # Usamos 10% para validación
    train_ds, eval_ds = split_dataset["train"], split_dataset["test"]
    print(f"INFO: Dataset de plantillas listo. Entrenamiento: {len(train_ds)} | Evaluación: {len(eval_ds)}")

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    output_dir_name = os.path.basename(OUTPUT_DIR)

    # --- TrainingArguments Optimizados ---
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=5, # Con datos de alta calidad, podemos entrenar un poco más
        learning_rate=1e-4,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",
        fp16=True,
        logging_dir=f"./logs/{output_dir_name}",
        logging_steps=10, # Logueamos más a menudo para ver el progreso
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
        tokenizer=tokenizer
    )

    print("\n" + "="*60)
    print("🚀  INICIANDO RE-ENTRENAMIENTO CON PLANTILLAS DE ALTA CALIDAD  🚀")
    print("="*60 + "\n")
    
    trainer.train()

    print("\nINFO: Guardando el mejor adaptador LoRA (v2)...")
    trainer.save_model(OUTPUT_DIR)
    
    print("\n" + "🏆"*10)
    print(f"✅ ¡RE-ENTRENAMIENTO COMPLETADO! El nuevo modelo está en: './{OUTPUT_DIR}'")
    print("🏆"*10)