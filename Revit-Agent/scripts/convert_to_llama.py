import json
import argparse
import os

SYSTEM_PROMPT = (
    "You are an expert C# programmer for the Autodesk Revit API. "
    "Your task is to generate a C# code snippet that can be executed directly "
    "to fulfill the user's request. Generate ONLY the raw C# code, without "
    "explanations, comments, or markdown formatting."
)

TEMPLATE = (
    "<s>[INST] <<SYS>>\n"
    "{system}\n"
    "<</SYS>>\n\n"
    "{prompt} [/INST]\n"
    "{completion}</s>"
)

def convert_jsonl(in_path: str, out_path: str):
    with open(in_path, "r", encoding="utf-8") as fin, \
         open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            prompt     = obj.get("prompt", "").strip()
            completion = obj.get("completion", "").rstrip()
            # monta el instruct
            instruct = TEMPLATE.format(
                system     = SYSTEM_PROMPT,
                prompt     = prompt,
                completion = completion
            )
            # escribimos una línea JSON con el campo "text"
            fout.write(json.dumps({"text": instruct}, ensure_ascii=False) + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Convierte tu JSONL {prompt,completion} en JSONL nativo Llama-Instruct"
    )
    parser.add_argument("input",  help="ruta a tu JSONL original")
    parser.add_argument("output", help="ruta al JSONL formateado que genera el script")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[!] archivo de entrada no encontrado: {args.input}")
        return

    convert_jsonl(args.input, args.output)
    print(f"[✓] conversion completada: {args.output}")

if __name__ == "__main__":
    main()