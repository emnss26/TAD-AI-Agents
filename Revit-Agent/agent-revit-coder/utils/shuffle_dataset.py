import pandas as pd

INPUT_FILE = "../data/train_data.jsonl" # Tu archivo con ~7600 variantes ordenadas
OUTPUT_FILE = "../data/train_data_shuffled.jsonl" # El archivo que usaremos para entrenar

print(f"Leyendo {INPUT_FILE}...")
# Usamos pandas porque es muy eficiente para manejar archivos grandes y barajar
df = pd.read_json(INPUT_FILE, lines=True)

# Barajamos el DataFrame de forma aleatoria
print("Barajando el dataset...")
df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Guardamos el resultado en un nuevo archivo JSONL
print(f"Guardando el dataset barajado en {OUTPUT_FILE}...")
df_shuffled.to_json(OUTPUT_FILE, orient='records', lines=True, force_ascii=False)

print(f"✅ ¡Proceso completado! {len(df_shuffled)} ejemplos han sido barajados.")
print(f"Usa '{OUTPUT_FILE}' como DATA_PATH en tu script de entrenamiento.")