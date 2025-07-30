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
    EarlyStoppingCallback
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# --- 1. FUNCIÓN DE FORMATEO Y TOKENIZACIÓN ---
def format_prompt_with_eos(tokenizer, example):
    return (
        f"### INSTRUCTION:\n{example['prompt']}\n\n"
        f"### RESPONSE:\n{example['completion']}{tokenizer.eos_token}"
    )

def tokenize_dataset(tokenizer, examples, max_length=512):
    formatted = [
        format_prompt_with_eos(tokenizer, {'prompt': p, 'completion': c})
        for p, c in zip(examples['prompt'], examples['completion'])
    ]
    tokenized = tokenizer(
        formatted,
        truncation=True,
        max_length=max_length,
        padding="max_length" # Usamos padding fijo para máxima compatibilidad
    )
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

def compute_metrics(eval_pred):
    # Esta es una métrica simple para pasar el eval_loss y que
    # load_best_model_at_end sepa qué monitorear.
    return {"eval_loss": eval_pred.metrics["eval_loss"]}

# --- 2. SETUP Y CONFIGURACIÓN ---
if __name__ == '__main__':
    MODEL_NAME  = "microsoft/phi-2"
    DATA_PATH   = os.path.join("data", "train_data.jsonl") 
    OUTPUT_DIR  = "lora_revit_agent_phi2_v9"

    print(f"INFO: CUDA disponible: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        raise RuntimeError("Se requiere GPU CUDA para este script.")

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.benchmark = True

    # --- 3. CARGA DEL MODELO Y TOKENIZER ---
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=quant_config,
        device_map={"": 0},
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()

    # --- 4. CONFIGURACIÓN DE LoRA (ALTA CAPACIDAD) ---
    lora_config = LoraConfig(
        r=16,
        lora_alpha=64,
        target_modules=["q_proj", "k_proj", "v_proj", "dense"],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    print("INFO: Modelo configurado para entrenamiento de alta capacidad con LoRA.")
    model.print_trainable_parameters()

    # --- 5. CARGA Y PROCESAMIENTO DEL DATASET ---
    print(f"INFO: Cargando dataset desde {DATA_PATH}...")
    raw_dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    split_dataset = raw_dataset.train_test_split(test_size=0.05, seed=42)
    train_ds, eval_ds = split_dataset["train"], split_dataset["test"]
    print(f"INFO: Tamaño de entrenamiento: {len(train_ds)} | Tamaño de evaluación: {len(eval_ds)}")

    MAX_LEN = 512
    tok_fn = functools.partial(tokenize_dataset, tokenizer, max_length=MAX_LEN)
    
    num_proc = max(1, os.cpu_count() // 1)
    print(f"INFO: Tokenizando con {num_proc} procesos y longitud máxima de {MAX_LEN}...")
    train_tok = train_ds.map(tok_fn, batched=True, remove_columns=train_ds.column_names, num_proc=num_proc)
    eval_tok  = eval_ds.map(tok_fn,  batched=True, remove_columns=eval_ds.column_names,  num_proc=num_proc)

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # --- 6. TrainingArguments (VERSIÓN MÁXIMA COMPATIBILIDAD) ---
    effective_batch_size = 2 * 1
    steps_per_epoch = max(1, len(train_tok) // effective_batch_size) 
    print(f"INFO: Pasos por época estimados: {steps_per_epoch}")
    
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=1,
        num_train_epochs=4,
        learning_rate=1e-4,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",

       do_eval=True,
       eval_steps=steps_per_epoch,       
       save_steps=steps_per_epoch,       
       save_total_limit=3,  

        bf16=True,
        group_by_length=False, 
        logging_dir="./logs",
        logging_steps=100,
        report_to="tensorboard"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tok,
        eval_dataset=eval_tok,
        data_collator=data_collator,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )

    # --- 7. ENTRENAMIENTO ---
    print("\n" + "="*60)
    print(f"🚀  INICIA ENTRENAMIENTO DEFINITIVO (MODO MÁXIMA COMPATIBILIDAD)  🚀")
    print(f"  - Dataset: {len(train_tok)} ejemplos")
    print(f"  - Épocas: {training_args.num_train_epochs}")
    print(f"  - Longitud de Secuencia: {MAX_LEN}")
    print(f"  - Rango LoRA (r): {lora_config.r}")
    print("="*60 + "\n")
    
    trainer.train()

    # --- 8. GUARDADO FINAL ---
    print("\nINFO: Guardando el último adaptador LoRA...")
    trainer.save_model(OUTPUT_DIR)
    
    print("\n" + "🏆"*10)
    print(f"✅ ¡MISIÓN CUMPLIDA! El entrenamiento ha finalizado.")
    print(f"✅ Revisa los checkpoints en './{OUTPUT_DIR}' para encontrar el de menor 'eval_loss'.")
    print("🏆"*10)