import os
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer # Usaremos SFTTrainer, es más moderno y funciona mejor con Unsloth
from dotenv import load_dotenv
from unsloth import FastLanguageModel

def run_training():
    # --- 1. Configuración ---
    load_dotenv()
    HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

    print(f"✅ GPU detectada y lista para la acción: {torch.cuda.get_device_name(0)}")

    # --- 2. Rutas y Modelo Base ---
    REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    BASE_MODEL = "microsoft/Phi-3-mini-4k-instruct"
    
    # Apuntamos al dataset legacy MIXTO
    DATA_PATH  = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_phi2_legacy_mixed.jsonl")
    OUTPUT_DIR = os.path.join(REPO_ROOT, "Revit-Agent", "training_artifacts_linux", "lora_revit_agent_phi3_v1_mixed_P71")

    # --- 3. Cargar Modelo y Tokenizer con Unsloth ---
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = BASE_MODEL,
        max_seq_length = 2048, # 4k es el máximo, 2k es seguro para VRAM
        dtype = None,
        load_in_4bit = True,
        token = HF_TOKEN,
    )
    
    # Unsloth se encarga de la preparación del modelo para QLoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16,
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha = 32,
        lora_dropout = 0.05,
        bias = "none",
        use_gradient_checkpointing = True,
        random_state = 3407,
    )
    model.print_trainable_parameters()

    # --- 4. Cargar y Formatear el Dataset ---
    # Unsloth prefiere un formato específico, lo creamos al vuelo
    def formatting_prompts_func(examples):
        prompts      = examples["prompt"]
        completions  = examples["completion"]
        texts = []
        for prompt, completion in zip(prompts, completions):
            texts.append(f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n{completion}<|end|>")
        return { "text" : texts, }

    print(f"Cargando y formateando el dataset desde: {DATA_PATH}")
    ds = load_dataset("json", data_files=DATA_PATH, split="train")
    ds = ds.shuffle(seed=42)
    ds = ds.map(formatting_prompts_func, batched = True,)
    
    split = ds.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]
    print(f"Dataset listo → Train: {len(train_ds)}, Eval: {len(eval_ds)}")

    # --- 5. Configurar y Lanzar el Trainer ---
    trainer = SFTTrainer(
        model = model,
        tokenizer = tokenizer,
        train_dataset = train_ds,
        eval_dataset = eval_ds,
        dataset_text_field = "text",
        max_seq_length = 2048,
        dataset_num_proc = 2,
        packing = False, # Lo dejamos en False para mayor simplicidad
        args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            per_device_train_batch_size = 1, # Seguro para 6GB VRAM
            gradient_accumulation_steps = 8, # Batch efectivo de 8
            num_train_epochs = 3,
            learning_rate = 2e-4,
            fp16 = not torch.cuda.is_bf16_supported(),
            bf16 = torch.cuda.is_bf16_supported(),
            logging_steps = 10,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "linear",
            seed = 3407,
            save_strategy="epoch",
        ),
    )
    
    print(f"🚀 Iniciando fine-tune con Phi-3 en Linux...")
    trainer.train()

    print(f"✅ Entrenamiento completado. Guardando modelo en {OUTPUT_DIR}")
    model.save_pretrained(OUTPUT_DIR)

# Protección para Windows/macOS (buena práctica)
if __name__ == "__main__":
    run_training()