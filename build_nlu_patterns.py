import os
import sys
import yaml

# --- Configuración de Rutas ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SHARED_LIBS_PATH = os.path.join(REPO_ROOT, 'Shared-Libs')
PATTERNS_FILE_PATH = os.path.join(SHARED_LIBS_PATH, 'nlu', 'patterns.yml')
sys.path.insert(0, SHARED_LIBS_PATH)

from nlu.language_assets import SYNONYMS

def build_intent_patterns():
    """
    Genera dinámicamente los patrones de intención basados en el diccionario SYNONYMS.
    """
    
    # Mapeo de verbos principales (claves de SYNONYMS) a un nombre de Intención base
    ACTION_MAP = {
        "crear": "Create", "genera": "Create", "dibuja": "Create", "construir": "Create",
        "inserta": "Insert", "coloca": "Insert", "añade": "Insert",
        "duplica": "Duplicate", "copia": "Duplicate", "clona": "Duplicate",
        "cambia": "Change", "modifica": "Change", "ajusta": "Change",
        "setea": "Set", "configura": "Set", "asigna": "Set", "define": "Set",
        "obtén": "Query", "extrae": "Query", "recupera": "Query", "lista": "Query", "encuentra": "Query",
        "borra": "Delete", "elimina": "Delete",
        "rota": "Rotate", "gira": "Rotate",
        "fija": "Pin", "bloquea": "Pin",
        "une": "Join",
        "exporta": "Export",
        "oculta": "Hide",
        "muestra": "Show",
        "tag": "Tag",
        # Añadir más mapeos base si es necesario...
    }

    # Palabras clave de objetos que definen la especificidad de la intención
    # Esto es crucial para diferenciar CreateWall de CreateFloor
    ENTITY_KEYWORDS = {
        'Wall': r'\b(muro|pared|wall)s?\b',
        'FamilyInstance': r'\b(instancia|familia|mobiliario|mueble|puerta|ventana|columna|pilar|viga|truss|celosía)s?\b',
        'Level': r'\b(nivel|planta|level)es\b',
        'Grid': r'\b(eje|rejilla|grid)s?\b',
        'Floor': r'\b(suelo|piso|losa|placa|floor|slab)s?\b',
        'Schedule': r'\b(tabla|planificación|schedule|cómputo)s?\b',
        'Workset': r'\b(workset|subproyecto)s?\b',
        'Opening': r'\b(agujero|hueco|apertura|opening|shaft)s?\b',
        'Dimension': r'\b(cota|dimensión|dimension)es\b',
        'Parameter': r'\b(parámetro|propiedad|comentario|marca|valor|parameter|property|comment|mark|value)s?\b',
        'Type': r'\b(tipo|type)s?\b',
        'Geometry': r'\b(geometr(í|i)a)s?\b',
        'View': r'\b(vista|view)s?\b',
    }

    intents = {}

    # Generar intenciones específicas (ej. CreateWall, DeleteFloor)
    for verb, base_intent in ACTION_MAP.items():
        verb_synonyms = [verb] + SYNONYMS.get(verb, [])
        verb_pattern = '|'.join(verb_synonyms)

        for entity_name, entity_pattern in ENTITY_KEYWORDS.items():
            intent_name = f"{base_intent}{entity_name}"
            
            # Crear patrón: (verbo) ... (entidad)
            # Ejemplo: \b(crea|genera|...)\s+.*\s+\b(muro|pared|...)\b
            pattern = rf'\b({verb_pattern})\b.*\s{entity_pattern}'
            
            if intent_name not in intents:
                intents[intent_name] = {'patterns': []}
            intents[intent_name]['patterns'].append(pattern)
    
    # Unificar patrones para la misma intención
    final_intents = {}
    for name, data in intents.items():
        if name not in final_intents:
            final_intents[name] = {'patterns': []}
        final_intents[name]['patterns'].extend(data['patterns'])
    
    return final_intents

def update_patterns_file(new_intents):
    """
    Lee el archivo patterns.yml, reemplaza la sección de 'intents' y lo guarda.
    """
    with open(PATTERNS_FILE_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    data['intents'] = new_intents
    
    with open(PATTERNS_FILE_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, indent=2)

    print(f"✅ Archivo '{PATTERNS_FILE_PATH}' actualizado con {len(new_intents)} intenciones generadas.")

if __name__ == "__main__":
    generated_intents = build_intent_patterns()
    update_patterns_file(generated_intents)