import json
import os

def load_catalog():
    """
    Carga el catálogo ENRIQUECIDO de la API y los datos de reflexión.
    Este es el único "conocimiento" que el orquestador necesita sobre la API.
    """
    base = os.path.dirname(__file__) + "/../data"
    
    # ¡IMPORTANTE! Apuntamos al nuevo archivo enriquecido que creamos con add_helpers.py
    catalog_path = os.path.join(base, "revit_api_catalog_enriched.json")
    reflection_path = os.path.join(base, "revit_api_reflection.json") # Este no cambia

    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: El catálogo enriquecido '{catalog_path}' no fue encontrado.")
        print("Por favor, ejecuta el script 'utils/add_helpers.py' primero para generarlo.")
        catalog = [] # Devuelve una lista vacía para evitar que el programa se caiga

    # La reflexión no se enriquece, se carga tal cual
    try:
        with open(reflection_path, 'r', encoding='utf-8') as f:
            reflection = json.load(f)
    except FileNotFoundError:
        print(f"ADVERTENCIA: El archivo de reflexión '{reflection_path}' no fue encontrado.")
        reflection = []

    return catalog, reflection