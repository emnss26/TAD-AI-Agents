import os
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model
from dotenv import load_dotenv

def run_training():
    # --- 1. Configuración ---
    load_dotenv()
    HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
    print(f"✅ Multi-GPU: {torch.cuda.device_count()} GPUs detectadas por PyTorch.")
    for i in range(torch.cuda.device_count()):
        print(f"  - GPU {i}: {torch.cuda.get_device_name(i)}")

    # --- 2. Rutas y Modelo Base ---
    REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    BASE_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
    DATA_PATH  = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_mistral.jsonl")
    OUTPUT_DIR = os.path.join(REPO_ROOT, "Revit-Agent", "training_artifacts", "lora_revit_agent_mistral_v1_MultiGPU_Final")

    # --- 3. Preparar Tokenizer y Modelo ---
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True, token=HF_TOKEN)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
        token=HF_TOKEN
    )

    # MEJORA CLAVE v22: Habilitar gradient checkpointing de la manera recomendada y compatible
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.config.use_cache = False

    lora_cfg = LoraConfig(
        r=16, lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    # --- 4. Cargar y Tokenizar el Dataset ---
    ds = load_dataset("json", data_files=DATA_PATH, split="train")
    def tokenize_fn(batch):
        tok = tokenizer(batch["text"], max_length=1024, truncation=True, padding="max_length")
        tok["labels"] = tok["input_ids"].copy()
        return tok
    tokenized = ds.map(tokenize_fn, batched=True, remove_columns=ds.column_names)
    
    split = tokenized.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # --- 5. Configurar y Lanzar el Trainer ---
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        optim="paged_adamw_8bit", # Volvemos al optimizador por defecto de QLoRA
        fp16=True,
        logging_steps=10,
        # MEJORA CLAVE v22: Sincronizar los argumentos con la llamada al modelo
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        evaluation_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        report_to="tensorboard",
    )

    trainer = Trainer(
        model=model, args=training_args, train_dataset=train_ds,
        eval_dataset=eval_ds, data_collator=data_collator,
    )
    
    print(f"🚀 Iniciando fine-tune Multi-GPU ESTABLE con Mistral-7B...")
    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    print(f"✅ Entrenamiento completado. Modelo guardado en {OUTPUT_DIR}")

if __name__ == "__main__":
    run_training()