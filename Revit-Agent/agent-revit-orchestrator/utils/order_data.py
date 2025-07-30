import json
import re

# Rutas (ajusta según tu estructura de carpetas)
INPUT_FILE = "../data/revit_api_reflection.json"
OUTPUT_FILE = "../data/revit_api_catalog.json"

def transform_reflection_to_catalog(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        classes = json.load(f)

    catalog = []
    for cls in classes:
        # Extraemos solo el nombre de la clase, sin el namespace
        type_name = cls["type"].split('.')[-1]

        # Procesamos cada método
        for method in cls.get("methods", []):
            sig = method["signature"]
            # Capturamos <returnType> <methodName>(<paramList>)
            m = re.match(r"^(\S+)\s+(\S+)\((.*)\)$", sig)
            if not m:
                continue
            return_type, name, params = m.groups()
            param_types = [p.strip() for p in params.split(',')] if params else []
            catalog.append({
                "name":       f"{type_name}.{name}",
                "return_type":    return_type,
                "parameter_types": param_types
            })

        # Convertimos cada propiedad en un getter sin parámetros
        for prop in cls.get("properties", []):
            catalog.append({
                "name":            f"{type_name}.get_{prop}",
                "return_type":     "unknown",
                "parameter_types": []
            })

    # Escribimos el JSON resultante
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"✅ Catálogo generado: {output_path}")

if __name__ == "__main__":
    transform_reflection_to_catalog(INPUT_FILE, OUTPUT_FILE)