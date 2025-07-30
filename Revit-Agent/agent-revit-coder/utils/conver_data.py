import json

IN  = "../agent-revit/data/train_data_final_generated.jsonl"
OUT = "../agent-revit/data/data_GPT_Fine_Tunning/train_data_finetunning_04.jsonl"

system_prompt = "Eres un asistente experto en la API de Revit. Responde siempre con código C# válido."

with open(IN, encoding="utf-8") as fin, open(OUT, "w", encoding="utf-8") as fout:
    for line in fin:
        ex = json.loads(line)
        # ex debe tener ex["prompt"] y ex["completion"]
        chat = {
            "messages": [
                {"role": "system",    "content": system_prompt},
                {"role": "user",      "content": ex["prompt"]},
                {"role": "assistant", "content": ex["completion"]}
            ]
        }
        fout.write(json.dumps(chat, ensure_ascii=False) + "\n")
print("→ Archivo listo:", OUT)