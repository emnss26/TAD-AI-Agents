import os
import torch
from datasets import load_dataset, Dataset
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
import shutil

# --- 1. Configuración y Carga de Credenciales ---
load_dotenv()
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

print(f"GPUs detectadas por PyTorch: {torch.cuda.device_count()}")
for i in range(torch.cuda.device_count()):
    print(f"  - GPU {i}: {torch.cuda.get_device_name(i)}")

# --- 2. Rutas y Nombres de Modelo/Dataset ---
REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BASE_MODEL = "mistralai/Mistral-7B-Instruct-v0.3" # VERSIÓN CORRECTA DEL MODELO
DATA_PATH  = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_llama.jsonl")
TOKENIZED_DATA_PATH = os.path.join(REPO_ROOT, "Revit-Agent", "training_artifacts", "tokenized_mistral_v03_dataset")
OUTPUT_DIR = os.path.join(REPO_ROOT, "Revit-Agent", "training_artifacts", "lora_revit_agent_mistral_v03_RTX4060")

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

print(f"⏳ Cargando el modelo base '{BASE_MODEL}' con mapeo de dispositivo inteligente...")
# MEJORA CLAVE v11.1: Invertir la asignación de memoria para usar la GPU 0 (RTX 4060) como principal
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=quant_config,
    device_map="auto",
    max_memory={0: "7GiB", 1: "1GiB"}, # GPU 0 (4060) es la principal, GPU 1 (5060 Ti) es la secundaria
    trust_remote_code=True,
    token=HF_TOKEN
)
print("✅ Modelo base cargado y distribuido entre las GPUs.")
print("Distribución de memoria del modelo:")
print(model.get_memory_footprint())

model.config.use_cache = False
# prepare_model_for_kbit_training se llama internamente cuando se usa device_map y quantization_config
model.gradient_checkpointing_enable()

lora_cfg = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_cfg)
model.print_trainable_parameters()

# --- 4. Cargar y Tokenizar el Dataset (con Caching) ---
# (Sin cambios en esta sección)
if os.path.exists(TOKENIZED_DATA_PATH):
    print(f"✅ Cargando dataset tokenizado desde caché: {TOKENIZED_DATA_PATH}")
    tokenized = Dataset.load_from_disk(TOKENIZED_DATA_PATH)
else:
    print(f"⏳ No se encontró caché. Tokenizando el dataset desde: {DATA_PATH}")
    ds = load_dataset("json", data_files=DATA_PATH, split="train")
    def tokenize_fn(batch):
        tok = tokenizer(batch["text"], max_length=1024, truncation=True, padding="max_length")
        tok["labels"] = tok["input_ids"].copy()
        return tok
    tokenized = ds.map(tokenize_fn, batched=True, num_proc=4, remove_columns=ds.column_names)
    print(f"✅ Tokenización completada. Guardando en caché...")
    tokenized.save_to_disk(TOKENIZED_DATA_PATH)

split = tokenized.train_test_split(test_size=0.1, seed=42)
train_ds, eval_ds = split["train"], split["test"]
print(f"Dataset listo → Train: {len(train_ds)}, Eval: {len(eval_ds)}")

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

# --- 5. Configurar y Lanzar el Trainer ---
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    num_train_epochs=3,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_ratio=0.03,
    optim="paged_adamw_8bit",
    fp16=True,
    gradient_checkpointing=True,
    logging_steps=20,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    report_to="tensorboard",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    data_collator=data_collator,
)

if __name__ == "__main__":
    print(f"🚀 Iniciando fine-tune LoRA con distribución Multi-GPU (Mistral-7B v0.3)...")
    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    print(f"✅ Entrenamiento completado. Modelo guardado en {OUTPUT_DIR}")