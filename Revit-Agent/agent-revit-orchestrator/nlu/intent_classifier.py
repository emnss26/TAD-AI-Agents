import re, yaml

cfg = yaml.safe_load(open("nlu/patterns.yml", encoding="utf-8"))
INTENTS = cfg["intents"]

def classify_intent(text: str) -> str:
    text = text.lower()
    # recorre intents y patrones
    for intent, block in INTENTS.items():
        for pat in block["patterns"]:
            if re.search(pat, text, re.IGNORECASE):
                return intent
    return "Unknown"