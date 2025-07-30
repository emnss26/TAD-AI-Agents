import os, json, re, glob
from bs4 import BeautifulSoup

# 1. Ajusta la ruta a tu carpeta de HTML extraídos
HTML_DIR = "../agent_revit_repos/revit-api-chms-main/html/2024/html"
OUTPUT   = "rag_corpus.jsonl"

if os.path.exists(OUTPUT):
    os.remove(OUTPUT)

def clean_text(s):
    return " ".join(s.split())

for html_path in glob.glob(os.path.join(HTML_DIR, "**", "*.htm*"), recursive=True):
    with open(html_path, encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")
    title_tag = soup.find(["h1","title"])
    paras     = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]

    if not title_tag or not paras:
        continue

    title = clean_text(title_tag.get_text())
    text  = clean_text(" ".join(paras))
    words = text.split()
    # chunk de ~200 palabras
    for i in range(0, len(words), 200):
        chunk = " ".join(words[i:i+200])
        record = {
            "id": f"{os.path.relpath(html_path, HTML_DIR)}#chunk{i//200}",
            "title": title,
            "text": chunk
        }
        with open(OUTPUT, "a", encoding="utf-8") as fw:
            fw.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"✅ {sum(1 for _ in open(OUTPUT))} fragmentos generados en {OUTPUT}")