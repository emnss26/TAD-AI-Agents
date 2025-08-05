import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import os
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
BASE_MODEL = "bigcode/starcoder"

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=quant_config,
    device_map="auto",
    trust_remote_code=True,
    token=HF_TOKEN
)

print(model)