import re, yaml
import os 

PATTERNS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patterns.yml')
try:
    with open(PATTERNS_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        INTENTS = cfg["intents"]
except FileNotFoundError:
    print(f"Error: El archivo de patrones no fue encontrado en {PATTERNS_PATH}")
    INTENTS = {}

def classify_intent(text: str) -> str:
    text = text.lower()
    # recorre intents y patrones
    for intent, block in INTENTS.items():
        for pat in block["patterns"]:
            if re.search(pat, text, re.IGNORECASE):
                return intent
    return "Unknown"