import os
import sys
import torch
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from dotenv import load_dotenv
import uvicorn

# --- 0. Configuración de Rutas y Logging (SIMPLE Y ROBUSTO) ---
# Sube dos niveles desde la ubicación de este archivo para encontrar la raíz del proyecto.
# Funciona en local (desde .../agent-revit-coder) y en Docker (desde /app/Revit-Agent/agent-revit-coder).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Añade la raíz al path para que las importaciones de shared_libs funcionen si las necesitas en el futuro.
sys.path.insert(0, REPO_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CoderAgent")

# --- 1. CONFIGURACIÓN ---
# Carga .env desde la raíz del proyecto para obtener el token de HF
load_dotenv(os.path.join(REPO_ROOT, '.env'))
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# Rutas al modelo base (online) y al adaptador LoRA (local)
BASE_MODEL_NAME = "meta-llama/CodeLlama-7b-instruct-hf"
LORA_PATH = os.path.join(REPO_ROOT, "lora_revit_agent_codellama_v1")

# --- 2. LÓGICA DE LA APP FASTAPI ---
app = FastAPI()
# Movemos las variables del modelo al contexto de la app para que estén disponibles
app.state.model = None
app.state.tokenizer = None

@app.on_event("startup")
def load_model():
    """
    Esta función se ejecutará UNA SOLA VEZ cuando Uvicorn inicie la aplicación.
    """
    logger.info("Iniciando la carga del modelo en el evento de startup de FastAPI...")
    
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    
    try:
        if not os.path.isdir(LORA_PATH):
             logger.error(f"CRÍTICO: La carpeta del modelo LoRA no se encontró en: {LORA_PATH}")
             logger.error("Asegúrate de que la carpeta del modelo entrenado 'lora_revit_agent_codellama_v1' esté en la raíz del proyecto.")
             return

        logger.info(f"Cargando modelo base '{BASE_MODEL_NAME}'...")
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_NAME,
            quantization_config=quant_config,
            device_map="auto",
            trust_remote_code=True,
            token=HF_TOKEN
        )

        logger.info(f"Cargando tokenizer para '{BASE_MODEL_NAME}'...")
        app.state.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True, token=HF_TOKEN)
        app.state.tokenizer.pad_token = app.state.tokenizer.eos_token

        logger.info(f"Aplicando adaptador LoRA desde '{LORA_PATH}'...")
        peft_model = PeftModel.from_pretrained(base_model, LORA_PATH)
        
        logger.info("Fusionando pesos de LoRA para optimizar la inferencia...")
        app.state.model = peft_model.merge_and_unload()
        app.state.model.eval()
        
        logger.info("✅ Modelo de Élite listo para recibir peticiones.")
        
    except Exception as e:
        logger.error(f"CRÍTICO: Falló la carga del modelo. El agente no podrá procesar peticiones.", exc_info=True)

class PromptRequest(BaseModel):
    prompt: str

@app.post("/predict")
async def predict(request: Request, body: PromptRequest):
    if not app.state.model or not app.state.tokenizer:
        raise HTTPException(status_code=503, detail="El modelo no está disponible o falló al cargar. Revise los logs del servidor.")
    
    try:
        full_prompt = body.prompt
        logger.info(f"Recibida petición del Orquestador.")
        
        inputs = app.state.tokenizer(full_prompt, return_tensors="pt").to(app.state.model.device)

        with torch.no_grad():
            outputs = app.state.model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.05,
                top_p=0.9,
                pad_token_id=app.state.tokenizer.eos_token_id,
                eos_token_id=app.state.tokenizer.eos_token_id
            )
        
        response_text = app.state.tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
        
        logger.info(f"Respuesta generada con éxito.")
        return {"code": response_text.strip()}

    except Exception as e:
        logger.error(f"Error durante la inferencia: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Agente Coder (CodeLlama-7b-LoRA) está en funcionamiento."}