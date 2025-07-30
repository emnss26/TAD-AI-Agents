import json

INPUT_FILE = "../data/train_data.jsonl"
print(f"Validando el archivo: {INPUT_FILE}\n")

line_number = 0
found_error = False

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        line_number += 1
        # Ignoramos líneas que estén completamente en blanco
        if not line.strip():
            continue
        
        try:
            # Intentamos cargar la línea como un objeto JSON
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f"❌ Error de formato JSON encontrado en la línea: {line_number}")
            print(f"   Contenido de la línea: {line.strip()}")
            print(f"   Detalle del error: {e}")
            found_error = True
            break # Nos detenemos en el primer error encontrado

if not found_error:
    print("✅ ¡Validación completada! El archivo parece tener un formato JSONL correcto.")