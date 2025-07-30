import re
import json
import random

# —— 1) Diccionario de sinónimos ——
synonyms = {
    # Español
    "crear":     ["generar", "construir", "modelar", "originar"],
    "genera":    ["crea", "construye", "modela"],
    "dibuja":    ["traza", "plasma", "representa"],
    "inserta":   ["coloca", "pone", "situa"],
    "añade":     ["agrega", "incorpora", "inserta"],
    "coloca":    ["sitúa", "ubica", "inserta"],
    "duplica":   ["reproduce", "copia", "clona"],
    "cambia":    ["modifica", "ajusta", "actualiza"],
    "obtén":     ["extrae", "recupera"],
    "setea":     ["configura", "asigna", "define"],
    "calcula":   ["determina", "estima", "suma"],
    "rota":      ["gira", "vira", "voltea"],
    "modela":    ["esculpe", "forma", "moldea"],
    "borra":     ["elimina", "suprime", "remueve"],
    # Inglés
    "create":    ["generate", "construct", "build"],
    "draw":      ["sketch", "plot", "render"],
    "insert":    ["place", "put", "position"],
    "add":       ["attach", "include", "append"],
    "duplicate": ["copy", "clone", "replicate"],
    "change":    ["modify", "adjust", "update"],
    "get":       ["retrieve", "fetch", "obtain"],
    "set":       ["define", "assign", "configure"],
    "calculate": ["compute", "determine", "estimate"],
    "rotate":    ["turn", "spin", "pivot"],
    "model":     ["shape", "form", "mold"],
    "delete":    ["remove", "erase", "clear"],
    "place":     ["insert", "position", "put"],
    "tag":       ["label", "mark", "annotate"],
}

# —— 2) Función para randomizar números (siempre enteros) ——
def randomize_numbers(prompt: str, code: str, variation: float = 0.2, n_variants: int = 3):
    nums = re.findall(r"(\d+(?:\.\d+)?)", prompt)
    variants = []
    for _ in range(n_variants):
        new_p = prompt
        new_c = code
        for num in nums:
            val = float(num)
            factor = random.uniform(1 - variation, 1 + variation)
            new_int = int(round(val * factor))
            new_p = new_p.replace(num, str(new_int), 1)
            new_c = re.sub(
                rf"UnitUtils\.ConvertToInternalUnits\(\s*{num}",
                f"UnitUtils.ConvertToInternalUnits({new_int}",
                new_c
            )
        variants.append((new_p, new_c))
    return variants

# —— 3) Función para aplicar sinónimos al verbo inicial ——
def apply_synonyms(prompt: str):
    for verb, syns in synonyms.items():
        if prompt.lower().startswith(verb + " "):
            for alt in syns:
                yield prompt.replace(verb, alt, 1)
    yield prompt  # también mantenemos el original

# —— 4) Generación de variantes de un ejemplo ——
def augment_example(prompt: str, code: str):
    all_variants = []
    for p_syn in apply_synonyms(prompt):
        # generamos 3 variantes numéricas de cada sinónimo / original
        for p_var, c_var in randomize_numbers(p_syn, code, variation=0.2, n_variants=3):
            all_variants.append({"prompt": p_var, "completion": c_var})
    # elegimos solo 2 variantes al azar (o menos si no hay suficientes)
    return random.sample(all_variants, k=min(2, len(all_variants)))

# —— 5) Variables de rutas ——
INPUT_PATH  = "../agent-revit/data/base_train_data.jsonl"
OUTPUT_PATH = "../agent-revit/data/augmented_train_data.jsonl"

# —— 6) Main ——
if __name__ == "__main__":
    random.seed(42)
    with open(INPUT_PATH, "r", encoding="utf-8") as fin, \
         open(OUTPUT_PATH, "w", encoding="utf-8") as fout:
        for line in fin:
            ex = json.loads(line)
            prompt     = ex["prompt"]
            completion = ex["completion"]

            # 1) Escribe el ejemplo original
            fout.write(json.dumps(ex, ensure_ascii=False) + "\n")

            # 2) Genera exactamente 2 augmentaciones y escríbelas
            for aug in augment_example(prompt, completion):
                fout.write(json.dumps(aug, ensure_ascii=False) + "\n")

    print(f"✅ Augmentación completada. Salida: {OUTPUT_PATH}")