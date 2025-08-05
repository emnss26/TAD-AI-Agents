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
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from dotenv import load_dotenv

# 0. Usar solo GPU 1
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

# 1. Carga de credenciales
load_dotenv()
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# 2. Rutas y modelo base
REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BASE_MODEL = "meta-llama/CodeLlama-7b-instruct-hf"

# Dataset templated
DATA_PATH  = os.path.join(
    REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_llama_templates.jsonl"
)
OUTPUT_DIR = os.path.join(
    REPO_ROOT, "Revit-Agent", "training_artifacts", "lora_revit_agent_codellama_v5"
)

# 3. Preparar tokenizer y modelo cuantizado + LoRA
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)
tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL, trust_remote_code=True, token=HF_TOKEN
)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=quant_config,
    device_map="auto",
    trust_remote_code=True,
    token=HF_TOKEN
)
model.config.use_cache = False
model = prepare_model_for_kbit_training(model)

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

# 4. Cargar y tokenizar el dataset templated
ds = load_dataset("json", data_files=DATA_PATH, split="train")

def tokenize_fn(batch):
    tok = tokenizer(
        batch["text"],
        max_length=1024,
        truncation=True,
        padding="max_length",
    )
    tok["labels"] = tok["input_ids"].copy()
    return tok

tokenized = ds.map(
    tokenize_fn,
    batched=True,
    remove_columns=ds.column_names,
)

split = tokenized.train_test_split(test_size=0.1, seed=42)
train_ds, eval_ds = split["train"], split["test"]
print(f"GPU1 → Train: {len(train_ds)}, Eval: {len(eval_ds)}")

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer, mlm=False
)

# 5. Configurar y lanzar el Trainer
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_ratio=0.03,
    optim="paged_adamw_8bit",
    fp16=True,
    logging_steps=20,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    data_collator=data_collator,
)

if __name__ == "__main__":
    print("🚀 GPU1: Fine-tune LoRA con datos templated …")
    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    print(f"✅ GPU1: Modelo guardado en {OUTPUT_DIR}")
