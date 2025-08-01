import os
import torch
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from dotenv import load_dotenv

# --- 0. Configuración del Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CoderAgent")

# --- 1. CONFIGURACIÓN Y CARGA DE MODELO ---
load_dotenv()
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# Rutas al modelo base y a tu adaptador LoRA entrenado
BASE_MODEL_NAME = "meta-llama/CodeLlama-7b-instruct-hf"
LORA_PATH = "./lora_revit_agent_codellama_v1" # La ruta es relativa a la raíz del proyecto

app = FastAPI()
model = None # Inicializamos el modelo como None

@app.on_event("startup")
def load_model():
    """
    Carga el modelo y el tokenizer al iniciar la aplicación.
    Esto evita la carga en frío en la primera petición.
    """
    global model, tokenizer
    
    logger.info("Iniciando la carga del modelo en el evento de startup...")
    
    # Configuración de cuantización
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    logger.info(f"Cargando modelo base '{BASE_MODEL_NAME}'...")
    try:
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_NAME,
            quantization_config=quant_config,
            device_map="auto",
            trust_remote_code=True,
            token=HF_TOKEN
        )

        logger.info(f"Cargando tokenizer para '{BASE_MODEL_NAME}'...")
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True, token=HF_TOKEN)
        tokenizer.pad_token = tokenizer.eos_token

        logger.info(f"Aplicando adaptador LoRA desde '{LORA_PATH}'...")
        model = PeftModel.from_pretrained(base_model, LORA_PATH)
        
        # Fusionamos los pesos para una inferencia ~30% más rápida. 
        # Esto consume un poco más de VRAM al inicio, pero vale la pena.
        logger.info("Fusionando pesos de LoRA en el modelo base para optimizar la inferencia...")
        model = model.merge_and_unload()
        model.eval()
        
        logger.info("✅ Modelo de Élite listo para recibir peticiones.")
    except Exception as e:
        logger.error(f"CRÍTICO: Falló la carga del modelo o del adaptador LoRA. El agente no podrá procesar peticiones. Error: {e}", exc_info=True)
        # El modelo se quedará como None, y la API devolverá un error.

# --- 2. LÓGICA DE LA API ---
class PromptRequest(BaseModel):
    prompt: str

@app.post("/predict")
async def predict(request: Request, body: PromptRequest):
    if not model:
        raise HTTPException(status_code=503, detail="El modelo no está disponible o falló al cargar. Revise los logs del servidor.")
    
    try:
        full_prompt = body.prompt
        logger.info(f"Recibida petición. Longitud del prompt: {len(full_prompt)} caracteres.")
        
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.05, # Muy bajo para respuestas deterministas y precisas
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        response_text = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
        
        logger.info(f"Respuesta generada con éxito. Longitud: {len(response_text)} caracteres.")
        return {"code": response_text.strip()}

    except Exception as e:
        logger.error(f"Error durante la inferencia: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Agente Coder (CodeLlama-7b-LoRA) está en funcionamiento."}