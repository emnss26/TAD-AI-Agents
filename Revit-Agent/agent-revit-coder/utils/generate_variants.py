import re
import json
import random

# Pool de datos para reemplazar entidades nombradas. La clave es un placeholder.
DATA_POOLS = {
    "level_name": ["Nivel 1", "Planta Baja", "Nivel 2", "Losa 100", "Primer Piso"],
    "view_name": ["Vista de Trabajo", "Plano de Fontanería", "Sección Longitudinal", "PLANTA PARA CLIENTE"],
    "wall_type_name": ["Muro Interior Acústico", "Exterior - Ladrillo", "Genérico - 250mm", "CW 100-25"],
    "family_name": ["M_Chair-Breuer", "Mesa de Oficina", "Puerta Sencilla", "Ventana Fija 120x60"],
    "material_name": ["Concreto", "Acero", "Vidrio Templado", "Roble Oscuro", "Pintura Blanca"],
    "workset_name": ["Arquitectura", "Estructura", "MEP", "Fachada", "Interiores"]
}

# —— 1) Diccionario de sinónimos ——
SYNONYMS = {
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

# --- 2. FUNCIONES DE AUMENTACIÓN REFINADAS ---

def augment_numbers(prompt, code, n_variants=10):
    """
    Aumenta números de forma inteligente, forzando a enteros si son parte de un nombre entre comillas.
    Garantiza la cantidad de variantes únicas solicitadas.
    """
    variants = {(prompt, code)}
    nums_in_prompt = re.findall(r'(?<!\w)(-?\d+\.?\d*)', prompt)
    
    if not nums_in_prompt:
        return list(variants)

    nums_in_code = re.findall(r'[(=,\s](-?\d+\.?\d*)', code)
    if len(nums_in_prompt) != len(nums_in_code):
        return list(variants)

    attempts = 0
    max_attempts = n_variants * 5

    while len(variants) < n_variants + 1 and attempts < max_attempts:
        attempts += 1
        new_prompt = prompt
        new_code = code
        
        for i in range(len(nums_in_prompt)):
            original_prompt_num_str = nums_in_prompt[i]
            original_code_num_str = nums_in_code[i]
            
            try:
                original_val = float(original_prompt_num_str)
            except ValueError:
                continue

            # ### LÓGICA DE CONTEXTO IMPLEMENTADA ###
            # Comprobar si el número está dentro de comillas en el prompt original.
            is_in_quotes = f'"{original_prompt_num_str}"' in prompt or f"'{original_prompt_num_str}'" in prompt or \
                           f'"{original_prompt_num_str.split(".")[0]}"' in prompt or f"'{original_prompt_num_str.split('.')[0]}'" in prompt

            if '.' in original_prompt_num_str and not is_in_quotes:
                # Es un decimal y NO está en un nombre -> variar como decimal.
                variation = random.uniform(0.1, 0.9) * random.choice([-1, 1])
                new_val = max(0.1, original_val + variation)
                new_val_str = f"{new_val:.1f}"
            else:
                # Es un entero O es un número dentro de un nombre -> FORZAR A ENTERO.
                variation = random.randint(1, 5) * random.choice([-1, 1])
                new_val = int(original_val) + variation
                new_val_str = str(max(1, new_val))

            new_prompt = re.sub(re.escape(original_prompt_num_str), new_val_str, new_prompt, 1)
            new_code = re.sub(re.escape(original_code_num_str), new_val_str, new_code, 1)

        variants.add((new_prompt, new_code))
            
    return list(variants)

def augment_named_entities(prompt, code):
    variants = [(prompt, code)]
    quoted_strings = re.findall(r'["\'](.*?)["\']', prompt)
    for original_string in quoted_strings:
        best_pool_key = None
        for key, pool in DATA_POOLS.items():
            if any(val.lower() in original_string.lower() or original_string.lower() in val.lower() for val in pool):
                best_pool_key = key
                break
        if best_pool_key:
            replacement = random.choice(DATA_POOLS[best_pool_key])
            if replacement.lower() != original_string.lower():
                new_prompt = prompt.replace(original_string, replacement)
                new_code = code.replace(original_string, replacement)
                variants.append((new_prompt, new_code))
    return list(set(variants))

def augment_verbs(prompt, code):
    variants = []
    words = prompt.split()
    if not words: return [(prompt, code)]
    first_verb = words[0].lower()
    if first_verb in SYNONYMS:
        for synonym in SYNONYMS[first_verb]:
            new_first_word = synonym.capitalize() if words[0][0].isupper() else synonym
            new_prompt = new_first_word + " " + " ".join(words[1:])
            variants.append((new_prompt, code))
    variants.append((prompt, code))
    return list(set(variants))

# --- 3. LÓGICA PRINCIPAL DE GENERACIÓN ---
def generate_variants(example):
    original_prompt = example["prompt"]
    original_code = example["completion"]
    all_variants = set()
    verb_variants = augment_verbs(original_prompt, original_code)
    entity_variants_stage = set(verb_variants)
    for p, c in verb_variants:
        entity_variants_stage.update(augment_named_entities(p, c))
    final_variants_stage = set(entity_variants_stage)
    for p, c in entity_variants_stage:
        final_variants_stage.update(augment_numbers(p, c))
    return [{"prompt": p, "completion": c} for p, c in final_variants_stage]

# --- 4. EJECUCIÓN ---
if __name__ == "__main__":
    INPUT_PATH  = "./data/base_train_data.jsonl"
    OUTPUT_PATH = "./data/train_data_final_generated.jsonl"
    
    random.seed(42)
    
    all_augmented_examples = []
    
    with open(INPUT_PATH, "r", encoding="utf-8") as fin:
        for i, line in enumerate(fin):
            if not line.strip(): continue
            try:
                example = json.loads(line)
                variants = generate_variants(example)
                all_augmented_examples.extend(variants)
            except json.JSONDecodeError:
                print(f"Advertencia: Se omitió la línea {i+1} por un error de formato JSON.")
                continue

    unique_examples = [dict(t) for t in {tuple(d.items()) for d in all_augmented_examples}]
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fout:
        for ex in unique_examples:
            fout.write(json.dumps(ex, ensure_ascii=False) + "\n")
            
    print(f"✅ Proceso de aumentación completado.")
    print(f"   Se generaron {len(unique_examples)} ejemplos únicos.")
    print(f"   Archivo de salida: {OUTPUT_PATH}")