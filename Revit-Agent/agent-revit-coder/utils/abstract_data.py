import os
import json
from bs4 import BeautifulSoup

INPUT_DIR = "../../agent_revit_repos/revit-api-chms-main/html/2025/html"
OUTPUT_FILE = "../data/revit_api_index.jsonl"

def extract_members(soup, section_name):
    """Busca <h2> o <h3> cuyo texto contenga section_name y extrae la siguiente <table>."""
    header = soup.find(lambda tag: tag.name in ("h2", "h3") and section_name in tag.get_text())
    if not header:
        return []
    table = header.find_next("table")
    if not table:
        return []
    members = []
    # Asume que la primera fila es cabecera
    for tr in table.find_all("tr")[1:]:
        cols = tr.find_all("td")
        if len(cols) >= 2:
            name = cols[0].get_text(strip=True)
            desc = cols[1].get_text(" ", strip=True)
            members.append({"name": name, "description": desc})
    return members

def parse_doc(html):
    soup = BeautifulSoup(html, "html.parser")
    data = {}

    # API Name
    api = soup.find("meta", {"name": "APIName"})
    data["api_name"] = api["content"] if api else None

    # Summary / Abstract
    summ = soup.find("meta", {"name": "Abstract"})
    if summ:
        data["summary"] = summ["content"]
    else:
        block = soup.find("div", class_="summary")
        data["summary"] = block.get_text(strip=True) if block else None

    # Syntax C#
    syntax = None
    for tag in soup.find_all(("h2","h3")):
        if "Syntax" in tag.get_text():
            pre = tag.find_next("pre")
            syntax = pre.get_text() if pre else None
            break
    data["syntax_csharp"] = syntax

    # Extract members
    data["methods"]    = extract_members(soup, "Methods")
    data["properties"] = extract_members(soup, "Properties")

    return data

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fout:
        for fname in os.listdir(INPUT_DIR):
            if not fname.lower().endswith(".htm"):
                continue
            path = os.path.join(INPUT_DIR, fname)
            html = open(path, encoding="utf-8", errors="ignore").read()
            info = parse_doc(html)
            info["source_file"] = fname
            fout.write(json.dumps(info, ensure_ascii=False) + "\n")
    print(f"✨ Extracción completada: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()