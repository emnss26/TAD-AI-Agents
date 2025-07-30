# prompt_builder.py
import json

# --- 1. Definición de los TEMPLATES para cada Intención ---
# Cada template ahora es una receta detallada para guiar al LLM.
TEMPLATES = {
    "CreateWall": {
        "api_context_query": "Wall.Create",
        "base_prompt": """
Generate C# Revit API code to create a wall.
User's original request: "{user_text}"

Key Parameters Extracted:
{formatted_slots}

**API Instructions & Best Practices:**
1.  Wrap the entire code in a `using (Transaction t = new Transaction(doc, "Create Wall")) {{ ... }}` block.
2.  If a specific wall type ('family_type') is provided, find it using a `FilteredElementCollector`. Otherwise, find the first available `WallType`.
3.  If a specific level name is provided, find it. Otherwise, find the first available `Level`.
4.  **Crucially, all length/height/thickness values must be converted to Revit's internal units (feet) using `UnitUtils.ConvertToInternalUnits()`.**
5.  Based on the parameters, create the wall's location curve (`Line` or `Arc`).
{dynamic_instructions}
6.  Use one of the `Wall.Create()` methods to build the wall.

**Available `Wall.Create` Signatures:**
{api_signatures}
""",
        "completion_hint": "using (Transaction t = new Transaction(doc, \"Create Wall\")) {{ t.Start();\n// Find Level and WallType\n// Create geometry Curve\n// Wall.Create(...);\nt.Commit(); }}"
    },
    "InsertFamilyInstance": {
        "api_context_query": "Document.Create.NewFamilyInstance",
        "base_prompt": """
Generate C# Revit API code to insert a family instance.

User's original request: "{user_text}"
Extracted Parameters:
{formatted_slots}

**API Instructions & Best Practices:**
1.  Wrap the entire code in a `using (Transaction t = new Transaction(doc, "Insert Instance")) {{ ... }}` block.
2.  Find the correct `FamilySymbol` for the category '{element_category}'. Filter by name if `family_type` is provided.
3.  **IMPORTANT: Before using the symbol, you MUST activate it** with `if (!symbol.IsActive) symbol.Activate();`.
4.  **IMPORTANT: If dimensions (width/height) are specified, you MUST first `.Duplicate()` the symbol to create a new type, and then set the dimension parameters on the *new* duplicated type.** This prevents modifying all instances of the original type.
5.  Determine the insertion point. If coordinates are given, use them. If a host object is mentioned, find its location.
6.  Use `doc.Create.NewFamilyInstance(...)` to place the element. Convert units where necessary.
""",
        "completion_hint": "using (Transaction t = new Transaction(doc, \"Insert Family Instance\")) {{ t.Start();\n// 1. Find FamilySymbol\n// 2. Duplicate if dimensions are present\n// 3. Activate symbol\n// 4. Determine insertion point\n// 5. doc.Create.NewFamilyInstance(...);\nt.Commit(); }}"
    },
    "CreateLevel": {
        "api_context_query": "Level.Create",
        "base_prompt": """
Generate C# Revit API code to create a new Level.

User's original request: "{user_text}"
Extracted Parameters:
{formatted_slots}

**API Instructions & Best Practices:**
1.  Use a transaction.
2.  The elevation value must be converted to internal units (feet).
3.  Use `Level.Create(doc, elevation)`.
4.  Set the name of the newly created level.

**Available `Level.Create` Signatures:**
{api_signatures}
""",
        "completion_hint": "using (Transaction t = new Transaction(doc, \"Create Level\")) {{ t.Start();\ndouble elevation = UnitUtils.ConvertToInternalUnits(...);\nLevel newLevel = Level.Create(doc, elevation);\nnewLevel.Name = ...;\nt.Commit(); }}"
    },
    "SetElementParameter": {
        "api_context_query": "Element.LookupParameter",
        "base_prompt": """
Generate C# Revit API code to modify a parameter on one or more elements.

User's original request: "{user_text}"
Extracted Parameters:
{formatted_slots}

**API Instructions & Best Practices:**
1.  Use a transaction.
{dynamic_instructions}
3.  For each element, find the parameter using `elem.LookupParameter("{parameter_name}")` or `elem.get_Parameter(BuiltInParameter...)`.
4.  Check if the parameter is not null and not read-only before setting its value with `.Set()`.
""",
        "completion_hint": "using (Transaction t = new Transaction(doc, \"Set Parameter\")) {{ t.Start();\n// 1. Get elements (from selection or collector)\n// 2. Loop through elements\n// 3. Find and set parameter\nt.Commit(); }}"
    },
    # DEFAULT TEMPLATE PARA CUBRIR TODOS LOS DEMÁS CASOS
    "DEFAULT": {
        "api_context_query": "",
        "base_prompt": """
Generate a complete, runnable C# Revit API code snippet to perform the following task. Assume `doc` and `uidoc` are available. If the task modifies the model, it must be wrapped in a transaction.

User's original request: "{user_text}"

I have extracted the following parameters from the request. Use them to guide the code generation:
{formatted_slots}

**Additional Guidance:**
{dynamic_instructions}
""",
        "completion_hint": "using (Transaction t = new Transaction(doc, \"General Task\"))\n{{\n    t.Start();\n\n    // Code based on user request and parameters\n\n    t.Commit();\n}}"
    }
}


# --- 2. Funciones Auxiliares ---
def _find_api_signatures(query: str, catalog: list) -> str:
    if not query or not catalog: return "No API context available."
    candidates = [m for m in catalog if m.get("name") == query or query in m.get("name", "")]
    if not candidates: return f"No signatures found for '{query}'."
    signatures = [f"{m.get('return_type', 'void')} {m.get('name')}({', '.join(m.get('parameter_types', []))})" for m in candidates]
    return "\n".join(signatures)

def _format_slots_for_prompt(slots: dict) -> str:
    if not slots: return "None"
    return "\n".join([f"- {key}: {value}" for key, value in slots.items()])


# --- 3. Función Principal de Construcción de Prompt ---
def build_request(intent: str, slots: dict, catalog: list, user_text: str) -> dict:
    """
    Construye la solicitud estructurada para el LLM, añadiendo lógica e instrucciones dinámicas.
    """
    template = TEMPLATES.get(intent, TEMPLATES["DEFAULT"])
    dynamic_instructions = []

    # --- Lógica Dinámica Específica por Intención ---
    if intent == 'CreateWall':
        if 'coordinates_xyz' in slots:
            dynamic_instructions.append("- The wall is defined by a start and end point provided in `coordinates_xyz`.")
        elif 'dimension_length' in slots:
            dynamic_instructions.append("- The wall is defined by a start point (assume `XYZ.Zero`) and a length (`dimension_length`). The direction is along the X-axis unless specified otherwise.")
    
    elif intent == 'SetElementParameter':
        if 'action_on_selection' in slots:
            dynamic_instructions.append("2. The user will select the elements. Get them using `uidoc.Selection.GetElementIds()`.")
        elif 'all_elements' in slots:
            dynamic_instructions.append("2. This applies to ALL elements of the specified category. Use a `FilteredElementCollector` to get them.")
        if 'level_name' in slots:
            dynamic_instructions.append("   - Further filter these elements by the specified level name.")

    # ... Aquí se puede añadir más lógica para otras intenciones a medida que se necesite.
    
    # Para el template DEFAULT, damos una guía genérica
    if intent not in TEMPLATES:
        dynamic_instructions.append("- Pay close attention to the user's request and the extracted parameters to infer the correct Revit API calls.")
        if 'action_on_selection' in slots:
            dynamic_instructions.append("- The user wants to select elements manually. Use `uidoc.Selection.PickObject` or `uidoc.Selection.GetElementIds`.")

    # --- Ensamblaje Final del Prompt ---
    formatted_slots = _format_slots_for_prompt(slots)
    final_prompt = template["base_prompt"].format(
        user_text=user_text,
        formatted_slots=formatted_slots,
        api_signatures=_find_api_signatures(template.get("api_context_query", ""), catalog),
        dynamic_instructions="\n".join(dynamic_instructions),
        **slots # Permite usar slots directamente como {element_category}
    ).strip()

    return {
        "llm_prompt": final_prompt,
        "code_completion_hint": template["completion_hint"].strip()
    }


# --- 4. Bloque de Prueba ---
if __name__ == '__main__':
    # Datos de prueba simulados
    mock_catalog = [
        {"name": "Wall.Create", "return_type": "Wall", "parameter_types": ["Document", "Curve", "ElementId", "ElementId", "Double", "Double", "Boolean", "Boolean"]},
        {"name": "Wall.Create", "return_type": "Wall", "parameter_types": ["Document", "IList<Curve>", "Boolean"]},
        {"name": "Document.Create.NewFamilyInstance", "return_type": "FamilyInstance", "parameter_types": ["XYZ", "FamilySymbol", "Element", "Level", "StructuralType"]}
    ]
    
    test_cases = [
        {
            "intent": "CreateWall",
            "text": "Crea un muro de 10 metros de largo y 3m de alto en el Nivel 1.",
            "slots": {"dimension_length": ("10", "metros"), "dimension_height": ("3", "m"), "level_name": "Nivel 1"}
        },
        {
            "intent": "InsertFamilyInstance",
            "text": "Inserta una ventana de 1.2x1.5 metros en un muro.",
            "slots": {"element_category": "ventana", "dimension_compound": ("1.2", "1.5"), "target_host": "en un muro"}
        },
        {
            "intent": "SetElementParameter",
            "text": "Cambia el comentario de todas las puertas a 'Revisar'.",
            "slots": {"all_elements": "todas las", "element_category": "puertas", "parameter_name": "comentario", "parameter_value": "'Revisar'"}
        },
        {
             "intent": "QueryElements",
             "text": "Dame el área total de todas las habitaciones.",
             "slots": {"all_elements": "todas las", "element_category": "habitaciones"}
        }
    ]

    for case in test_cases:
        request_for_llm = build_request(case["intent"], case["slots"], mock_catalog, case["text"])
        print(f"--- PROMPT PARA INTENCIÓN: {case['intent']} ---")
        print(request_for_llm["llm_prompt"])
        print("\n" + "="*80 + "\n")