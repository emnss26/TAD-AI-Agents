import traceback
import os
import re
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, StoppingCriteria, StoppingCriteriaList
from peft import PeftModel

# --- 1. CONFIGURACIÓN ---
app = FastAPI()
BASE_MODEL = "microsoft/phi-2"
LORA_PATH = "./lora_revit_agent_phi2_v7" # O la versión final que estés usando (v9, etc.)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"INFO: Usando dispositivo: {DEVICE}")

# --- 2. CARGA DEL MODELO LoRA ---
print("INFO: Cargando modelo base y tokenizer...")
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=quant_config,
    device_map=None,
    trust_remote_code=True
)

print(f"INFO: Cargando adaptador LoRA desde {LORA_PATH}...")
model = PeftModel.from_pretrained(base_model, LORA_PATH)
model.to(DEVICE)
model.eval()
print("INFO: Modelo de Élite listo para inferencia en GPU.")

# --- 3. LÓGICA DE PARADA PERSONALIZADA ---
class StopOnTokens(StoppingCriteria):
    def __init__(self, stop_token_ids):
        self.stop_token_ids = stop_token_ids

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        for stop_ids in self.stop_token_ids:
            if len(input_ids[0]) >= len(stop_ids):
                if torch.all(input_ids[0][-len(stop_ids):] == stop_ids):
                    return True
        return False

# --- 4. LÓGICA DE LA APLICACIÓN ---
class Prompt(BaseModel):
    prompt: str

@app.get("/")
async def root():
    return {"message": "Agente de IA para Revit (Élite v1.5 - Modo Pulido) está en funcionamiento."}

@app.post("/predict")
async def predict(body: Prompt):
    try:
        # --- PASO 1: CONSTRUIR PROMPT Y CRITERIOS DE PARADA ---
        full_prompt = f"### INSTRUCTION:\n{body.prompt.strip()}\n\n### RESPONSE:\n"
        print(f"\n--- PROMPT ENVIADO AL MODELO ---\n{full_prompt}\n---------------------------------\n")

        stop_token_strings = ["### INSTRUCTION:", "//", "/*", "using ("]
        stop_token_ids = [
            tokenizer(t, return_tensors='pt')['input_ids'][0].to(DEVICE) 
            for t in stop_token_strings
        ]
        
        stopping_criteria = StoppingCriteriaList([StopOnTokens(stop_token_ids)])

        inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=1024).to(DEVICE)

        # --- PASO 2: GENERACIÓN CONTROLADA ---
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.01,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                stopping_criteria=stopping_criteria
            )

        # --- PASO 3: POST-PROCESAMIENTO IMPLACABLE (v3) ---
        raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        if "### RESPONSE:" in raw_output:
            raw_code = raw_output.split("### RESPONSE:")[1].strip()
        else:
            raw_code = tokenizer.decode(outputs[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True).strip()

        noise_signals = ["//", "/*", "###"]
        earliest_noise_index = len(raw_code)
        for signal in noise_signals:
            index = raw_code.find(signal)
            if index != -1 and index < earliest_noise_index:
                earliest_noise_index = index
        
        clean_code = raw_code[:earliest_noise_index].strip()

        # ### CORRECCIÓN QUIRÚRGICA ###:
        # En lugar de buscar la ÚLTIMA llave, ahora buscaremos la PRIMERA.
        # Esto cortará eficazmente la cadena de llaves repetidas justo después
        # de que se cierre el bloque de código principal.
        if '}' in clean_code:
            first_brace_index = clean_code.find('}')
            clean_code = clean_code[:first_brace_index + 1]

        print(f"\n--- CÓDIGO PURO GENERADO (PULIDO) ---\n{clean_code}\n---------------------------------\n")
        return {"code": clean_code}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en el servidor del agente: {str(e)}")

# --- 5. PUNTO DE ENTRADA ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)