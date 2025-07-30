#!/usr/bin/env python3
import json
import re
import copy
import random

INPUT_PATH  = "../agent-revit/rag_database/revit_api_reference_dataset.jsonl"
OUTPUT_PATH = "auto_train_examples.jsonl"

def parse_reference_to_example(ref):
    # ref: dict con "prompt" y "completion"
    # Extrae nombre tras "Referencia API Revit: X Method/Property"
    m = re.search(r"Referencia API Revit: (.+?)(?: Method| Property)", ref["prompt"])
    if not m:
        return None
    name = m.group(1).strip()
    
    # Busca firma C# tras "Syntax C# public ...;"
    m2 = re.search(r"Syntax C# (public .+?);", ref["completion"], re.DOTALL)
    if not m2:
        return None
    sig = m2.group(1) + ";"
    
    # Construye el prompt en español
    prompt = f"Invoca el método {name} en la API de Revit con sus parámetros adecuados."
    # Extrae nombres de parámetros desde la firma
    params = re.findall(r'\w+\s+(\w+)', sig)
    completion = f"{name}({', '.join(params)});"
    
    return {"prompt": prompt, "completion": completion}

def generate_variants(example, n=3):
    # Solo genera variantes si contiene dimensiones
    m = re.search(r"\(([\d\.]+),([\d\.]+),([\d\.]+)\).*?alto\s*([\d\.]+)m", example["prompt"])
    if not m:
        return []
    sx, sy, sz, h = map(float, m.groups())
    level_match = re.search(r"en\s+([A-Za-z0-9 ]+)\s+de", example["prompt"])
    level = level_match.group(1) if level_match else "Nivel 1"
    
    variants = []
    for _ in range(n):
        f = random.uniform(0.8,1.2)
        sx2, sy2, sz2 = round(sx*f,2), round(sy*f,2), round(sz*f,2)
        ex2, ey2, ez2 = round((sx+5)*f,2), round(sy*f,2), round(sz*f,2)
        h2 = round(h*f,2)
        lvl_num = re.search(r"(\d+)", level)
        lvl = int(lvl_num.group(1))+random.choice([-1,0,1]) if lvl_num else 1
        lvl = max(1,lvl)
        level2 = f"Nivel {lvl}"
        p = f"Crea un muro en {level2} de ({sx2},{sy2},{sz2}) a ({ex2},{ey2},{ez2}) alto {h2}m."
        ex2 = copy.deepcopy(example)
        ex2["prompt"] = p
        variants.append(ex2)
    return variants

# 1) Parsear y generar ejemplos
examples = []
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        ref = json.loads(line)
        ex = parse_reference_to_example(ref)
        if ex:
            examples.append(ex)

# 2) Crear variantes
all_examples = []
for ex in examples:
    all_examples.append(ex)
    vars = generate_variants(ex, n=3)
    all_examples.extend(vars)

# 3) Guardar en JSONL
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for ex in all_examples:
        f.write(json.dumps(ex, ensure_ascii=False) + "\n")

print(f"✅ Generados {len(all_examples)} ejemplos en {OUTPUT_PATH}")
