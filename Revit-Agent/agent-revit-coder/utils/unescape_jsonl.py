import json
from pathlib import Path

# Define file names
files = [
    ("../agent-revit/data/cleaned_success.jsonl", "cleaned_success_unescaped.jsonl"),
    ("../agent-revit/data/cleaned_failed_full.jsonl", "compiled_failed_unescaped.jsonl")
]

# Process each file
for infile, outfile in files:
    input_path = Path(infile)
    output_path = Path(outfile)
    if input_path.exists():
        with input_path.open('r', encoding='utf-8') as fin, output_path.open('w', encoding='utf-8') as fout:
            for line in fin:
                try:
                    obj = json.loads(line)
                    fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

print("✅ Archivos unescaped generados:")
for _, outfile in files:
    if Path(outfile).exists():
        print(f"- {outfile}")