import os
import json
import glob
import re
from pathlib import Path

# 1. Ajusta esta ruta si tu carpeta es distinta
#    Por defecto asume:
#    C:\Users\<tu_usuario>\OneDrive\Escritorio\TAD-AI-Agents\agent_revit_repos\RevitSdkSamples-master\SDK\Samples
SDK_SAMPLES_DIR = Path(__file__).parent.parent / "agent_revit_repos" / "RevitSdkSamples-master" / "SDK" / "Samples"

OUTPUT = Path(__file__).parent / "sdk_finetune.jsonl"
if OUTPUT.exists():
    OUTPUT.unlink()

# Palabras clave/patrones de llamadas a la API que queremos conservar
API_PATTERNS = [
    r"\.Create\(",
    r"FilteredElementCollector",
    r"UnitUtils\.",
    r"CurveLoop",
    r"Line\.CreateBound",
    r"Grid\.Create",
    r"Floor\.Create",
    r"Wall\.Create",
    # añade aquí más patrones según tus necesidades
]

count = 0
for cs_path in glob.glob(f"{SDK_SAMPLES_DIR}/**/*.cs", recursive=True):
    rel = Path(cs_path).relative_to(SDK_SAMPLES_DIR)
    prompt = f"Ejemplo de uso de Revit API para `{rel.with_suffix('')}`"

    # Leemos tolerando errores de codificación
    with open(cs_path, encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()

    # Buscamos la lógica entre la primera '{' y la última '}'
    try:
        start = next(i for i, l in enumerate(lines) if "{" in l)
        end   = len(lines) - next(i for i, l in enumerate(reversed(lines)) if "}" in l) - 1
    except StopIteration:
        continue

    raw_snippet = "\n".join(lines[start+1:end])

    # Filtramos línea a línea por patrones de API
    filtered_lines = []
    for line in raw_snippet.splitlines():
        if any(re.search(pat, line) for pat in API_PATTERNS):
            filtered_lines.append(line.strip())

    final_snippet = "\n".join(filtered_lines).strip()

    # Descartamos snippets muy cortos
    if len(final_snippet.split()) < 5:
        continue

    # Escribimos el ejemplo limpio en JSONL
    with open(OUTPUT, "a", encoding="utf-8") as fw:
        fw.write(json.dumps({
            "prompt": prompt,
            "completion": final_snippet
        }, ensure_ascii=False) + "\n")
    count += 1

if count > 0:
    print(f"✅ {count} ejemplos generados en {OUTPUT}")
else:
    print("⚠️  No se generó ningún ejemplo. Revisa que SDK_SAMPLES_DIR apunte al directorio correcto.")