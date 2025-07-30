# nlu/slot_filler.py
import re
import os
import yaml

# --- 1. Carga de Configuración ---
# Cargar todos los patrones de slots definidos en el archivo YML.
# Usamos la última versión de los slots que creamos, con unidades imperiales incluidas.
PATTERNS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patterns.yml')
try:
    with open(PATTERNS_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        ALL_SLOTS_PATTERNS = cfg["slots"]
        
except FileNotFoundError:
    print("Error: 'nlu/patterns.yml' no encontrado. Asegúrate de que el archivo existe en la carpeta nlu/.")
    ALL_SLOTS_PATTERNS = {}

# --- 2. Mapeo de Inteligencia: Intención -> Slots Relevantes ---
# Este es el cerebro del orquestador. Define qué información buscar para cada acción.
INTENT_SLOTS_MAPPING = {
    # --- Creación de Elementos ---
    'CreateWall': [
        'element_category', 'dimension_length', 'dimension_height', 'dimension_thickness',
        'family_type', 'level_name', 'coordinates_xyz', 'structural_usage'
    ],
    'InsertFamilyInstance': [
        'element_category', 'family_type', 'level_name', 'coordinates_xy',
        'coordinates_xyz', 'target_host', 'dimension_width', 'dimension_height', 
        'dimension_compound', 'structural_usage'
    ],
    'CreateLevel': [
        'new_name_definition', 'level_name', 'dimension_offset', 'level_elevation'
    ],
    'CreateGrid': [
        'quantity', 'element_category', 'orientation', 'dimension_spacing'
    ],
    'CreateFloor': [
        'element_category', 'dimension_compound', 'dimension_thickness', 'level_name'
    ],
    'CreateRoof': [
        'element_category', 'level_name' # La geometría es más compleja, a menudo implícita
    ],
    'CreatePipe': [
        'element_category', 'dimension_diameter'
    ],
    'CreateDuct': [
        'element_category', 'dimension_compound' # para ancho x alto
    ],
    'CreateRailing': [
        'element_category', 'target_host' # "en una escalera"
    ],
    'CreateOpening': [
        'action_on_selection', 'target_host', 'dimension_compound', 'dimension_length'
    ],
    'CreateColumnsAtIntersections': [
        'element_category', 'family_type', 'all_elements' # "en todos los cruces"
    ],
    'CreateBeamBetweenColumns': [
        'element_category', 'orientation' # "alineadas horizontalmente"
    ],
    'CreateSheet': [
        'element_category', 'new_name_definition', 'parameter_value' # para número de plano
    ],
    'CreateSchedule': [
        'element_category', 'new_name_definition', 'parameter_name' # para los campos
    ],
    'CreateWorkset': [
        'quantity', 'element_category', 'new_name_definition'
    ],
    'CreateMaterial': [
        'material_name', 'color_name'
    ],
    'CreateView': [
        'view_name', 'new_name_definition', 'level_name', 'orientation', 'coordinates_xyz'
    ],

    # --- Modificación de Elementos ---
    'SetElementParameter': [
        'all_elements', 'element_category', 'level_name', 'parameter_name', 
        'parameter_value', 'action_on_selection', 'family_type'
    ],
    'ChangeElementType': [
        'all_elements', 'action_on_selection', 'element_category', 'family_type'
    ],
    'RenameElements': [
        'all_elements', 'element_category', 'view_name', 'new_name_definition', 
        'name_prefix', 'action_on_selection'
    ],
    'MoveElement': [
        'action_on_selection', 'element_category', 'dimension_generic_with_unit', 'direction_vector'
    ],
    'RotateElement': [
        'action_on_selection', 'angle_degrees'
    ],
    'PinElements': [
        'all_elements', 'action_on_selection', 'element_category'
    ],
    'DeleteElements': [
        'all_elements', 'element_category', 'active_context', 'level_name'
    ],
    'DuplicateType': [
        'element_category', 'family_type', 'new_name_definition', 'dimension_thickness'
    ],
    'DuplicateView': [
        'active_context', 'view_name', 'new_name_definition'
    ],
    'CopyElements': [
        'all_elements', 'element_category', 'level_name' # Captura nivel origen y destino
    ],

    # --- Acciones de Vista y Documento ---
    'ChangeViewProperties': [
        'active_context', 'all_elements', 'view_name', 'parameter_value' # "escala a 50", "detalle a 'Medio'"
    ],
    'ChangeElementVisibility': [
        'active_context', 'action_on_selection', 'element_category', 'all_elements'
    ],
    'ApplyViewTemplate': [
        'active_context', 'view_name', 'all_elements'
    ],
    'ExportFile': [
        'active_context', 'file_format', 'file_path', 'view_name', 'element_category'
    ],
    'LoadFamily': [
        'file_path'
    ],
    'SyncWithCentral': [
        'parameter_value' # para el comentario
    ],
    'PlaceViewOnSheet': [
        'view_name', 'level_name' # level_name puede capturar 'Planta Baja'
    ],

    # --- Acciones Geométricas y de Anotación ---
    'JoinGeometry': [
        'element_category' # Espera dos categorías
    ],
    'PaintFace': [
        'material_name', 'element_category', 'orientation' # "cara interior"
    ],
    'CreateDimension': [
        'action_on_selection', 'element_category'
    ],
    'TagElement': [
        'all_elements', 'active_context', 'element_category'
    ],
    
    # --- Consultas ---
    'QueryElements': [
        'all_elements', 'element_category', 'level_name', 'parameter_name', 'parameter_value'
    ],
    
    'Unknown': []
}


# --- 3. Función de Extracción ---
def extract_slots(text: str, intent: str) -> dict:
    """
    Extrae las entidades (slots) relevantes de un texto, basado en una intención dada.
    """
    relevant_slot_names = INTENT_SLOTS_MAPPING.get(intent, [])
    if not relevant_slot_names:
        return {}

    extracted_slots = {}
    
    # Iterar SÓLO sobre los slots relevantes y buscar sus patrones.
    for slot_name in relevant_slot_names:
        pattern = ALL_SLOTS_PATTERNS.get(slot_name)
        if not pattern:
            print(f"Advertencia: El slot '{slot_name}' definido en el mapeo no tiene un patrón en patterns.yml.")
            continue

        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            processed_matches = []
            for match in matches:
                if isinstance(match, tuple):
                    # Filtrar grupos vacíos de la tupla.
                    # Ej: ('10', '.0', 'm') -> ['10.0', 'm']
                    # Ej: ('10', '', 'm') -> ['10', 'm']
                    non_empty_groups = [group for group in match if group]
                    if len(non_empty_groups) == 1:
                        processed_matches.append(non_empty_groups[0])
                    elif len(non_empty_groups) > 1:
                        processed_matches.append(tuple(non_empty_groups))
                else:
                    processed_matches.append(match)

            if len(processed_matches) == 1:
                extracted_slots[slot_name] = processed_matches[0]
            elif len(processed_matches) > 1:
                 # Si encontramos múltiples valores para el mismo slot, los guardamos como una lista.
                 # Ej: "unir muros y suelos" -> element_category: ['muros', 'suelos']
                extracted_slots[slot_name] = processed_matches

    return extracted_slots

# --- 4. Bloque de Prueba ---
if __name__ == '__main__':
    # Simula la clasificación de intención
    test_cases = [
        {"text": "Crea un muro del tipo 'Genérico - 200mm' en el 'Nivel 1' de 8 metros de largo y 3m de alto.", "intent": "CreateWall"},
        {"text": "Selecciona todos los muros del 'Nivel 2' y cambia su comentario a 'REVISAR AISLAMIENTO'.", "intent": "SetElementParameter"},
        {"text": "Genera un piso rectangular de 10x8 pies.", "intent": "CreateFloor"},
        {"text": "Crea 8 ejes horizontales separados por 10 metros.", "intent": "CreateGrid"},
        {"text": "Une la geometría de una columna y un suelo.", "intent": "JoinGeometry"},
        {"text": "Oculta los elementos seleccionados en la vista activa.", "intent": "ChangeElementVisibility"},
        {"text": "Exporta la vista 3D activa a NWC", "intent": "ExportFile"},
        {"text": "Crea una nueva tabla de planificación para puertas", "intent": "CreateSchedule"}
    ]

    for case in test_cases:
        print(f"--- Texto: \"{case['text']}\" ---")
        print(f"Intención Detectada: {case['intent']}")
        slots = extract_slots(case['text'], case['intent'])
        print(f"Slots Extraídos: {slots}\n")