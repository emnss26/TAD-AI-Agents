# main (agent_server.py)
import traceback
import os
import re
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from peft import PeftModel

# --- 1. CONFIGURACIÓN ---
app = FastAPI()
BASE_MODEL = "microsoft/phi-2"
# *** CAMBIO IMPORTANTE: Usamos el modelo que demostró ser más robusto ***
LORA_PATH = "./lora_revit_agent_phi2_v7" 
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"INFO: Usando dispositivo: {DEVICE}")

# --- 2. CARGA DEL MODELO LoRA ---
print("INFO: Cargando modelo base y tokenizer...")
quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=quant_config, device_map="auto", trust_remote_code=True)
print(f"INFO: Cargando adaptador LoRA desde {LORA_PATH}...")
model = PeftModel.from_pretrained(base_model, LORA_PATH)
model.eval()
print("INFO: Modelo de Élite listo para inferencia.")

# --- 3. LÓGICA DE LIMPIEZA QUIRÚRGICA ---
def surgical_clean_code(raw_text: str) -> str:
    """
    Función de post-procesamiento definitiva para aislar únicamente el código C#.
    """
    # Corregir problemas de codificación comunes primero
    try:
        text = raw_text.encode('latin-1').decode('utf-8')
    except UnicodeDecodeError:
        text = raw_text
    
    # 1. Encontrar el inicio del código buscando palabras clave C#
    code_starters = ["using ", "UIDocument ", "Level ", "WallType ", "string ", "double ", "List<", "FamilySymbol ", "Element ", "ICollection<"]
    start_index = -1
    for starter in code_starters:
        index = text.find(starter)
        if index != -1:
            if start_index == -1 or index < start_index:
                start_index = index
    
    if start_index == -1:
        # Si no encontramos un inicio claro, no podemos limpiar de forma segura.
        return f"// ERROR: No se encontró un punto de inicio de código C# válido en la salida del modelo.\n// Salida cruda: {text}"

    code_block = text[start_index:]
    
    # 2. Encontrar el final del código balanceando las llaves {}
    open_braces = 0
    last_brace_index = -1
    for i, char in enumerate(code_block):
        if char == '{':
            open_braces += 1
        elif char == '}':
            open_braces -= 1
            if open_braces == 0:
                last_brace_index = i
                break # Encontramos el final del bloque principal
    
    if last_brace_index != -1:
        return code_block[:last_brace_index + 1].strip()
    else:
        # Si no hay llaves (código de una línea o incompleto), devolvemos hasta el primer salto de línea.
        return code_block.split('\n')[0].strip()

# --- 4. LÓGICA DE LA APLICACIÓN ---
class Prompt(BaseModel):
    prompt: str

@app.get("/")
async def root():
    return {"message": "Agente de IA para Revit (Élite v3.0 - Modo Quirúrgico) está en funcionamiento."}

@app.post("/predict")
async def predict(body: Prompt):
    try:
        # Usamos el formato que funcionó mejor con el modelo v7
        full_prompt = f"### INSTRUCTION:\n{body.prompt.strip()}\n\n### RESPONSE:\n"
        print(f"\n--- PROMPT ENVIADO AL MODELO ---\n{full_prompt}\n---------------------------------\n")

        inputs = tokenizer(full_prompt, return_tensors="pt", return_attention_mask=True).to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.01,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        raw_output = tokenizer.decode(outputs[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True).strip()
        
        # Usamos nuestra nueva función de limpieza
        final_code = surgical_clean_code(raw_output)
        
        print(f"\n--- CÓDIGO PURO GENERADO (LIMPIEZA QUIRÚRGICA) ---\n{final_code}\n---------------------------------\n")
        return {"code": final_code}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en el servidor del agente: {str(e)}")

# --- 5. PUNTO DE ENTRADA ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)