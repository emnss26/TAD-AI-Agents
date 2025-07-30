import os, sys, json


REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SHARED_LIBS_PATH = os.path.join(REPO_ROOT, 'Shared-Libs')
sys.path.insert(0, SHARED_LIBS_PATH)

from nlu.intent_classifier import classify_intent
from nlu.slot_filler import extract_slots


IN_FILE   = os.path.join(REPO_ROOT, 'Revit-Agent', 'agent-revit-orchestrator', 'data', 'train_data.jsonl')
OUT_FILE  = os.path.join(REPO_ROOT, 'Revit-Agent', 'agent-revit-orchestrator', 'data', 'train_data_rag_format.jsonl')


def transform():
    with open(IN_FILE, 'r', encoding='utf-8') as fin, \
         open(OUT_FILE, 'w', encoding='utf-8') as fout:

        for line in fin:
            try:
                obj = json.loads(line)
                # Obtenemos la petición del usuario, soportando diferentes claves
                user_request = (
                    obj.get('prompt')
                    or obj.get('completion') # A veces la petición está en la clave 'completion' en algunos formatos
                    or ""
                ).split('\n')[0] # Nos aseguramos de tomar solo la primera línea si hay saltos.
                
                if not user_request:
                    continue

                # Aquí está la lógica correcta
                intent = classify_intent(user_request)
                # ---- LA CORRECCIÓN ----
                # Pasamos tanto el texto como la intención a extract_slots
                slots  = extract_slots(user_request, intent)

                # Creamos el nuevo objeto con el formato RAG
                # NOTA: Por ahora, `RELEVANT_API_CONTEXT` estará vacío. Se llenará en la Fase 2 del plan.
                new_obj = {
                    "USER_REQUEST": user_request,
                    "DETECTED_INTENT": intent,
                    "EXTRACTED_SLOTS": slots,
                    "RELEVANT_API_CONTEXT": [] # Placeholder para el futuro RAG
                }
                fout.write(json.dumps(new_obj, ensure_ascii=False) + "\n")
            except json.JSONDecodeError:
                print(f"Advertencia: Se omitió una línea mal formada: {line.strip()}")
                continue

if __name__ == "__main__":
    print(f"Transformando {IN_FILE} -> {OUT_FILE} ...")
    transform()
    print("¡Listo! El archivo transformado se ha guardado.")