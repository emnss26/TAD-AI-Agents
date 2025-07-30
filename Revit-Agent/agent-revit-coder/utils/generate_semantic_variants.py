# -*- coding: utf-8 -*-
"""
Generador de Variantes Semánticas v4.1 (Final - Robust Replacement)
Activo Crítico del Proyecto: Agente de IA para Revit

Misión:
Este script transforma un conjunto de plantillas de alta calidad en un dataset
masivo y diverso. Utiliza un método de reemplazo de texto robusto para evitar
conflictos entre los placeholders de Python y la sintaxis de C#.

Estrategia:
1.  **Carga de Plantillas Humanas:** Carga plantillas desde un archivo .jsonl
    donde cada plantilla ha sido creada por un experto.
2.  **Generación de Parámetros:** Para cada variante, genera un diccionario de
    valores aleatorios a partir de los DATA_POOLS.
3.  **Reemplazo Robusto:** Itera sobre el diccionario de parámetros y reemplaza
    explícitamente cada placeholder en la plantilla, en lugar de usar .format().
4.  **Balance y Aleatoriedad:** Asegura una representación equitativa de las
    plantillas y baraja el dataset final.
"""
import json
import random
import sys
import collections

# --------------------------------------------------------------------------
# --- CONFIGURACIÓN ---
# --------------------------------------------------------------------------
INPUT_TEMPLATES_FILE = "../data/template_data.jsonl"
OUTPUT_DATASET_FILE = "../data/train_data_final_generated.jsonl"
NUM_VARIANTS_PER_TEMPLATE = 3
GLOBAL_SEED = 42

# --------------------------------------------------------------------------
# --- DATA POOLS (EL COMBUSTIBLE PARA LA VARIEDAD) ---
# --------------------------------------------------------------------------
# (Este diccionario debe ser el más completo que hemos compilado)
DATA_POOLS = {
    "level_name": ["Level 1", "Nivel 1", "Planta Baja", "First Floor", "L01", "Level 2", "Nivel 2", "Roof", "Azotea", "Basement"],
    "wall_type_name": ["Generic - 200mm", "Exterior - Brick on Mtl. Stud", "Muro Básico 15cm", "SW12"],
    "floor_type_name": ["Generic 12\"", "Suelo Hormigón 30cm", "Wood Joist 10\"", "Concrete - 225mm"],
    "roof_type_name": ["Generic - 400mm", "Basic Roof - Steel Truss", "Cubierta Inclinada - Teja"],
    "pipe_type_name": ["Standard", "PVC - Sch 40", "Acero - Carbono"],
    "duct_type_name": ["Default", "Rectangular - Mitered Elbows", "Redondo - Taps"],
    "conduit_type_name": ["EMT", "RMC", "PVC Conduit"],
    "window_type_name": ["M_Fixed", "Ventana Fija 1.20x1.50", "Standard Window"],
    "door_type_name": ["M_Single-Flush", "Puerta 90x210", "Double-Glass"],
    "column_type_name": ["W-Wide Flange-Column", "HSS-Hollow", "Pilar 30x60"],
    "beam_type_name": ["W-Wide Flange", "UB-Universal Beam"],
    "furniture_type_name": ["Desk", "Mesa-Oficina", "Chair-Executive"],
    "sprinkler_type_name": ["Pendent - Hosted", "Upright - Non-Hosted"],
    "air_terminal_type_name": ["Supply Diffuser", "Return Grille"],
    "family_category": ["OST_Windows", "OST_Doors", "OST_Furniture", "OST_PlumbingFixtures", "OST_MechanicalEquipment", "OST_LightingFixtures", "OST_ElectricalEquipment", "OST_Sprinklers", "OST_DuctTerminal", "OST_StructuralColumns", "OST_StructuralFraming", "OST_StructuralFoundation", "OST_Rebar"],
    "system_family_category": ["OST_Walls", "OST_Floors", "OST_Ceilings", "OST_Roofs", "OST_Stairs", "OST_Ramps"],
    "mep_curve_category": ["OST_PipeCurves", "OST_DuctCurves", "OST_CableTray", "OST_Conduit"],
    
    # Valores numéricos
    "length_m": [5.0, 7.8, 10.2, 15.0], "height_m": [2.8, 3.0, 3.15], "width_m": [1.0, 0.9, 1.2],
    "elevation_m": [3.5, 4.0, -3.0], "spacing_m": [6, 8, 10], "angle_degrees": [30, 45, 90],
    "thickness_cm": [10, 15, 20, 25, 30], "pipe_diameter_mm": [50, 80, 100, 150], "num_items": [5, 8, 10],

    # Grupos Compuestos
    "floor_size_m": [(10, 8), (12.5, 6.2)], "duct_size_mm": [(300, 200), (450, 250)],
    "single_point": [(2, 3, 0), (7, 4, 3)], "coordinates": [(0, 0, 0, 10, 0, 0), (5, 5, 3, 15, 5, 3)],
    
    # Texto
    "parameter_value": ["REVISAR", "APROBADO", "RF-90"]
}

# --------------------------------------------------------------------------
# --- LÓGICA DE GENERACIÓN ---
# --------------------------------------------------------------------------

def expand_vars(vars_needed, pools):
    # ... (Esta función no cambia)
    params = {}
    for var in vars_needed:
        if var not in pools:
            continue
        val = random.choice(pools[var])
        if var == "floor_size_m":
            params["floor_w_m"], params["floor_l_m"] = val
        elif var == "duct_size_mm":
            params["duct_width_mm"], params["duct_height_mm"] = val
        elif var == "single_point":
            params["x1"], params["y1"], params["z1"] = val
        elif var == "coordinates":
            params.update(dict(zip(["x1", "y1", "z1", "x2", "y2", "z2"], val)))
        else:
            params[var] = val
    return params

def generate_variants_for_template(template, pools, num_variants):
    """Genera variantes para una plantilla usando reemplazo de texto explícito."""
    random.seed(hash(template['prompt_template']))
    variants = []
    
    p_tpl = template["prompt_template"]
    c_tpl = template["completion_template"]
    vars_needed = template["vars_needed"]

    for _ in range(num_variants):
        params = expand_vars(vars_needed, pools)
        
        # **LÓGICA DE REEMPLAZO ROBUSTA**
        new_prompt = p_tpl
        new_completion = c_tpl
        for key, value in params.items():
            placeholder = "{" + key + "}"
            new_prompt = new_prompt.replace(placeholder, str(value))
            new_completion = new_completion.replace(placeholder, str(value))
            
        variants.append({"prompt": new_prompt, "completion": new_completion})
            
    return variants

# --------------------------------------------------------------------------
# --- EJECUCIÓN PRINCIPAL ---
# --------------------------------------------------------------------------

if __name__ == "__main__":
    print("="*70)
    print("🚀 INICIO: Generador de Dataset v4.1 (Robust Replacement) 🚀")
    print("="*70)

    try:
        with open(INPUT_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
            templates = [json.loads(line) for line in f if line.strip()]
        print(f"INFO: Se cargaron {len(templates)} plantillas desde '{INPUT_TEMPLATES_FILE}'.")
    except FileNotFoundError:
        print(f"⛔ ERROR CRÍTICO: No se encontró el archivo de plantillas '{INPUT_TEMPLATES_FILE}'.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"⛔ ERROR CRÍTICO: El archivo de plantillas contiene un JSON mal formado. Error: {e}")
        sys.exit(1)

    if not templates:
        print("ADVERTENCIA: Archivo de plantillas vacío.")
        sys.exit(0)

    print(f"INFO: Generando {NUM_VARIANTS_PER_TEMPLATE} variantes por cada plantilla...")
    final_dataset = []
    for template in templates:
        if not all(k in template for k in ["prompt_template", "completion_template", "vars_needed"]):
             print(f"ADVERTENCIA: Saltando plantilla por formato incorrecto: {template}")
             continue
        variants = generate_variants_for_template(template, DATA_POOLS, NUM_VARIANTS_PER_TEMPLATE)
        final_dataset.extend(variants)
    
    print(f"INFO: Total de ejemplos generados: {len(final_dataset)}")
    
    random.seed(GLOBAL_SEED)
    random.shuffle(final_dataset)
    
    print(f"INFO: Guardando {len(final_dataset)} ejemplos en '{OUTPUT_DATASET_FILE}'...")
    with open(OUTPUT_DATASET_FILE, 'w', encoding='utf-8') as f:
        for example in final_dataset:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print("\n" + "🏆"*25)
    print("✅ ¡MISIÓN CUMPLIDA! El dataset de élite ha sido generado.".center(70))
    print(f"✅ Archivo final: '{OUTPUT_DATASET_FILE}' con {len(final_dataset)} ejemplos.".center(70))
    print("✅ Listo para la fase de entrenamiento con `train_lora.py`.".center(70))
    print("🏆"*25)