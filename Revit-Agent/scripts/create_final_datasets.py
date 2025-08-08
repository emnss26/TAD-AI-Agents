import json
import os
import random
import re

# --- CONFIGURACIÓN (sin cambios) ---
REPO_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INPUT_FILE = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "templates_with_semantic_variants.jsonl")
MISTRAL_EXPLICIT_OUT = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_mistral_explicit.jsonl")
MISTRAL_MIXED_OUT = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_mistral_mixed.jsonl")
PHI3_EXPLICIT_OUT = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_phi3_explicit.jsonl")
PHI3_MIXED_OUT = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_phi3_mixed.jsonl")
PHI2_LEGACY_EXPLICIT_OUT = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_phi2_legacy_explicit.jsonl")
PHI2_LEGACY_MIXED_OUT = os.path.join(REPO_ROOT, "Revit-Agent", "agent-revit-coder", "data", "train_data_phi2_legacy_mixed.jsonl")

NUM_EXPLICIT_VARIANTS = 4


# MEJORA: DATA_POOLS masivo y completo basado en tu inventario.
DATA_POOLS = {
    # --- Nombres y Strings ---
    "beam_name": ["B-1", "B-2", "Viga Principal", "Viga Secundaria"],
    "bottom_level_name": ["Nivel 01", "Planta Baja", "Sotano -1", "Foundation Level"],
    "category_name": ["Muros", "Puertas", "Ventanas", "Pisos"],
    "column_type_name": ["Hormigon-Rectangular-30x60", "Steel W-Shape", "Pilar Circular 45cm"],
    "comment": ["VERIFICAR CON ESTRUCTURA", "Aprobado por Arquitectura", "Instalacion final"],
    "door_name": ["Puerta Principal", "Puerta de Servicio", "D-101"],
    "door_type_name": ["Simple-1 Hoja", "Doble Vidriada", "Cortafuegos 60min"],
    "element_name": ["Elemento-01", "Muro-Divisorio", "Viga-Carga"],
    "family_name": ["M_Puerta-Simple", "M_Ventana-Fija", "M_Escritorio", "M_Silla-Ejecutiva"],
    "file_name": ["Exportacion_Revit", "Plano_Nivel_1", "Modelo_Coordinacion"],
    "filter_name": ["Filtro de Fases", "Ocultar MEP", "Resaltar Estructura"],
    "fire_rating": ["60 min", "90 min", "N/A"],
    "fire_rating_value": ["60 min", "90 min", "N/A"],
    "floor_type_name": ["Concreto 20cm", "Madera-Entablonado", "Piso Tecnico"],
    "item_name": ["Mobiliario Especial", "Equipo Mecanico", "Detalle Constructivo"],
    "level1_name": ["Nivel 1", "Planta Baja", "L01"],
    "level2_name": ["Nivel 2", "Planta Alta", "L02"],
    "level_name": ["Nivel 1", "Nivel 2", "Planta Baja", "Azotea"],
    "level_to_duplicate": ["Nivel 2", "Nivel 3"],
    "link_name": ["ARQ_Modelo_Vinculado.rvt", "EST_Modelo_Vinculado.rvt"],
    "mark_value": ["M-01", "P-02a", "V-103b"],
    "material_name": ["Concreto", "Acero", "Vidrio", "Madera de Roble", "Ladrillo Comun"],
    "new_family_name": ["Familia Puerta Corregida", "Ventana Parametrica Nueva"],
    "new_level_name": ["Nivel Nuevo", "Entre-piso", "Azotea Superior"],
    "new_name": ["Nombre Corregido", "Version Final", "Elemento Actualizado"],
    "new_text": ["Texto Actualizado", "Revisar Nota"],
    "new_type_name": ["Tipo Duplicado", "Nuevo Estilo de Muro", "Ventana-02"],
    "note_text": ["Revisar especificaciones del ingeniero.", "Cota a eje.", "Pendiente 2%"],
    "old_name": ["Nombre Antiguo", "Version Preliminar", "Elemento Obsoleto"],
    "old_type_name": ["Tipo a Reemplazar", "Estilo Antiguo"],
    "original_level_name": ["Nivel a Copiar", "Nivel Base"],
    "original_name": ["Nombre Original", "Familia Base"],
    "original_type_name": ["Tipo Original", "Muro Generico 15cm"],
    "panel_name": ["Panel de Iluminacion", "Panel de Control"],
    "param_name": ["Comentarios", "Marca", "Clasificacion OmniClass"],
    "parameter_name": ["Comentarios", "Marca", "Clasificacion OmniClass"],
    "parameter_value": ["Valor A", "Fase 2", "Revisado"],
    "pattern_name": ["Diagonal", "Concreto", "Solido", "Tierra"],
    "pipe_type_name": ["Tuberia de Acero", "PVC Sanitario"],
    "plane_name": ["Plano de Referencia Central", "Eje A", "Plano Superior"],
    "prefix": ["ARQ-", "EST-", "MEP-"],
    "room_name": ["Oficina 101", "Sala de Reuniones", "Lobby Principal"],
    "schedule_name": ["Tabla de Puertas", "Planificacion de Muros"],
    "selection_prompt": ["Seleccione los elementos a modificar", "Elija un muro anfitrion"],
    "shape_name": ["Forma Extruida", "Caja Generica"],
    "sheet_name": ["A101 - Plantas", "A201 - Elevaciones"],
    "source_level": ["Nivel 1", "Planta Baja"],
    "target_level": ["Nivel 2", "Planta Alta"],
    "template_name": ["Plantilla de Vista Arquitectonica", "Seccion Fuga"],
    "text_note": ["NOTA GENERAL 1", "VER DETALLE 05"],
    "text_to_find": ["Revisar", "Temporal", "ANTIGUO"],
    "title_block_size": ["A0", "A1 Metrico"],
    "transaction_name": ["Crear Elementos", "Modificar Parametros"],
    "type_name_substring": ["Generico", "Concreto", "Madera"],
    "unit_name": ["Metros", "Pies", "Pulgadas"],
    "view_name": ["Planta Nivel 1", "Seccion Longitudinal", "Vista 3D Isométrica"],
    "wall_name": ["Muro Exterior", "Tabique Interior"],
    "wall_type_name": ["Muro Generico - 20cm", "Tabique Yeso 10cm"],
    "window_name": ["Ventana-01", "Ventana Baño"],
    "workset_name": ["Estructura", "Arquitectura", "MEP"],

    # --- Números: Integers y Floats ---
    "angle_degrees": [15.0, 30.0, 45.0, 90.0],
    "color_b": [0, 64, 128, 255], "color_g": [0, 128, 255], "color_r": [255, 128, 0],
    "cols": [3, 4, 5, 10], "rows": [3, 4, 5, 10],
    "depth_m": [0.5, 1.0, 5.0], "diameter_inch": [2.0, 4.0, 6.0], "diameter_mm": [50.0, 100.0, 150.0],
    "distance_m": [1.0, 2.5, 5.0, 10.0], "elevation_m": [-0.5, 0.0, 3.0, 6.5],
    "eye_x_m": [-50.0, 0.0, 50.0], "eye_y_m": [-50.0, 0.0, 50.0], "eye_z_m": [1.6, 10.0, 30.0],
    "height": [3.0, 4.0, 5.0], "height_m": [3.0, 4.5, 9.0], "height_mm": [2100.0, 2400.0, 3000.0],
    "length_m": [2.0, 5.0, 10.25, 25.0], "num_grids": [3, 5, 8], "num_horizontal": [4, 6], "num_vertical": [5, 7], "num_worksets": [3, 5],
    "offset_m": [0.5, 1.0, -0.25], "p1x_m": [-10.0, 0.0], "p1y_m": [-10.0, 0.0], "p1z_m": [0.0, 3.0],
    "p2x_m": [10.0, 20.0], "p2y_m": [10.0, 20.0], "p2z_m": [0.0, 3.0], "radius_m": [1.0, 2.5, 5.0],
    "separation_m": [4.0, 6.0, 8.5], "sheet_number": ["A-101", "S-202", "M-001"],
    "sill_height_m": [0.8, 0.9, 1.1], "sill_height_mm": [800.0, 900.0, 1100.0],
    "size_m": [1.0, 2.0, 5.0], "slope_percentage": [1.0, 2.0, 5.0], "spacing_m": [3.0, 6.0, 7.5],
    "start_x": [-5.0, 0.0], "start_y": [-5.0, 0.0], "start_z": [0.0, 2.75],
    "end_x": [15.0, 25.0], "end_y": [15.0, 25.0], "end_z": [0.0, 2.75],
    "text_size_mm": [1.8, 2.5, 3.5], "thickness_cm": [10.0, 15.0, 20.0, 30.0], "thickness_mm": [100.0, 150.0, 200.0],
    "transparency_percent": [10, 30, 50, 80], "value": [100.0, 250.5, 500.0], "value_m": [10.0, 25.5, 50.0],
    "width_cm": [10.0, 15.0, 20.0], "width_m": [0.9, 1.2, 3.0], "width_mm": [900.0, 1200.0, 1500.0],
    "x1": [-10.0, 0.0, 5.0], "x2": [10.0, 20.0, 25.0], "x_m": [1.0, 5.0, 10.0],
    "y1": [-10.0, 0.0, 5.0], "y2": [10.0, 20.0, 25.0], "y_m": [1.0, 5.0, 10.0],
    "z1": [0.0, 3.0, 6.0], "z2": [0.0, 3.0, 9.0], "z_m": [0.0, 1.5, 3.0],

    # --- ENUMS (Se deben manejar como strings que el código pueda parsear) ---
    "built_in_category_enum": ["OST_Walls", "OST_Doors", "OST_Windows", "OST_Floors"],
    # Corregido typo
    "buit_in_category_enum": ["OST_Walls", "OST_Doors", "OST_Windows", "OST_Floors"],
}

# Lógica inspirada en tu validador de C#
def get_random_value(var_name):
    # ... (sin cambios)
    if var_name in DATA_POOLS: return random.choice(DATA_POOLS[var_name])
    low = var_name.lower()
    if any(s in low for s in ["name", "comment", "material", "family", "type", "prefix", "text", "path", "prompt", "content"]):
        return f"Mock_{var_name.replace('_', ' ').title().replace(' ', '')}_{random.randint(1, 100)}"
    if any(s in low for s in ["percent", "num", "rows", "cols", "color"]):
        return random.randint(1, 100)
    return round(random.uniform(1.0, 50.0), 2)

# MEJORA CLAVE v2.6: La función de relleno más robusta hasta la fecha.
def fill_template(prompt, completion, variables):
    
    # Paso 1: Encontrar todos los placeholders que existen en CUALQUIERA de los dos strings.
    placeholders_in_prompt = set(re.findall(r'\{(\w+)\}', prompt))
    placeholders_in_completion = set(re.findall(r'\{(\w+)\}', completion))
    all_placeholders = placeholders_in_prompt.union(placeholders_in_completion)

    # Paso 2: Generar valores aleatorios para cada placeholder encontrado.
    replacements = {}
    for var in all_placeholders:
        replacements[var] = get_random_value(var)

    # Paso 3: Reemplazar de forma segura en ambos strings.
    filled_prompt = prompt
    filled_completion = completion
    
    for var, value in replacements.items():
        str_value = str(value)
        placeholder = f"{{{var}}}"
        
        filled_prompt = filled_prompt.replace(placeholder, str_value)
        filled_completion = filled_completion.replace(placeholder, str_value)
        
    return filled_prompt, filled_completion

def format_for_model(prompt, completion, model_type):
    if model_type == 'mistral':
        return f"<s>[INST] {prompt} [/INST]{completion}</s>"
    elif model_type == 'phi3':
        return f"<|user|>\n{prompt}<|end|>\n<|assistant|>\n{completion}<|end|>"
    return ""

def main():
    print(f"Leyendo plantillas con variantes semánticas desde: {INPUT_FILE}")
    templates = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip(): templates.append(json.loads(line))
    print(f"Se cargaron {len(templates)} plantillas.")

    with open(MISTRAL_EXPLICIT_OUT, 'w', encoding='utf-8') as f_me, \
         open(MISTRAL_MIXED_OUT, 'w', encoding='utf-8') as f_mm, \
         open(PHI3_EXPLICIT_OUT, 'w', encoding='utf-8') as f_pe, \
         open(PHI3_MIXED_OUT, 'w', encoding='utf-8') as f_pm, \
         open(PHI2_LEGACY_EXPLICIT_OUT, 'w', encoding='utf-8') as f_ple, \
         open(PHI2_LEGACY_MIXED_OUT, 'w', encoding='utf-8') as f_plm:
        
        for i, tpl in enumerate(templates):
            if (i + 1) % 1000 == 0:
                print(f"Procesando plantilla {i+1}/{len(templates)}...")

            prompt_tpl, completion_tpl, vars_needed = tpl.get("prompt_template", ""), tpl.get("completion_template", ""), tpl.get("vars_needed", [])
            
            # --- MIXED (con placeholders) ---
            f_mm.write(json.dumps({"text": format_for_model(prompt_tpl, completion_tpl, 'mistral')}) + '\n')
            f_pm.write(json.dumps({"text": format_for_model(prompt_tpl, completion_tpl, 'phi3')}) + '\n')
            f_plm.write(json.dumps({"prompt": prompt_tpl, "completion": completion_tpl}) + '\n')

            # --- EXPLICIT (con valores) ---
            for _ in range(NUM_EXPLICIT_VARIANTS):
                # Usamos la nueva función robusta
                prompt_exp, completion_exp = fill_template(prompt_tpl, completion_tpl, vars_needed)
                
                f_me.write(json.dumps({"text": format_for_model(prompt_exp, completion_exp, 'mistral')}) + '\n')
                f_mm.write(json.dumps({"text": format_for_model(prompt_exp, completion_exp, 'mistral')}) + '\n')
                f_pe.write(json.dumps({"text": format_for_model(prompt_exp, completion_exp, 'phi3')}) + '\n')
                f_pm.write(json.dumps({"text": format_for_model(prompt_exp, completion_exp, 'phi3')}) + '\n')
                f_ple.write(json.dumps({"prompt": prompt_exp, "completion": completion_exp}) + '\n')
                f_plm.write(json.dumps({"prompt": prompt_exp, "completion": completion_exp}) + '\n')

    total_explicit = len(templates) * NUM_EXPLICIT_VARIANTS
    total_mixed = len(templates) * (NUM_EXPLICIT_VARIANTS + 1)
    print("\n✅ Proceso completado.")
    print(f"   - Archivos 'Explicit' generados con ~{total_explicit} ejemplos.")
    print(f"   - Archivos 'Mixed' generados con ~{total_mixed} ejemplos.")

if __name__ == "__main__":
    main()