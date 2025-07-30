# utils/add_helpers.py
import json
import os

# --- Configuración de Rutas ---
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CATALOG_IN = os.path.join(ROOT, "data", "revit_api_catalog.json")
CATALOG_OUT = os.path.join(ROOT, "data", "revit_api_catalog_enriched.json")

# --- Lista de Helpers Conceptuales (Versión Expandida y Definitiva) ---
HELPERS = [
    # === 1. BÚSQUEDA Y FILTRADO DE ELEMENTOS (LOS MÁS IMPORTANTES) ===
    {
        "name": "Document.GetFirstOrDefaultElementOfType",
        "description": "Finds the first available element of a specific class (e.g., WallType, Level). Ideal for getting default types when none is specified.",
        "return_type": "Autodesk.Revit.DB.Element",
        "parameter_types": ["Autodesk.Revit.DB.Document", "System.Type"]
    },
    {
        "name": "Document.GetFirstOrDefaultElementOfCategory",
        "description": "Finds the first available element instance of a specific BuiltInCategory (e.g., OST_Windows, OST_Walls).",
        "return_type": "Autodesk.Revit.DB.Element",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.BuiltInCategory"]
    },
    {
        "name": "Document.GetFirstOrDefaultElementTypeOfCategory",
        "description": "Finds the first available ELEMENT TYPE (like FamilySymbol or WallType) of a specific BuiltInCategory. Essential for creating new instances.",
        "return_type": "Autodesk.Revit.DB.ElementType",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.BuiltInCategory"]
    },
    {
        "name": "Document.GetAllElementsOfCategory",
        "description": "Gets a list of all element instances of a specific BuiltInCategory.",
        "return_type": "System.Collections.Generic.List<Autodesk.Revit.DB.Element>",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.BuiltInCategory"]
    },
    {
        "name": "Document.FindElementByName",
        "description": "Finds a specific element by its name (e.g., a Level named 'Nivel 1', or a WallType named 'Genérico - 200mm'). This is a very common operation.",
        "return_type": "Autodesk.Revit.DB.Element",
        "parameter_types": ["Autodesk.Revit.DB.Document", "System.Type", "string"]
    },
    {
        "name": "Document.FindElementsByParameterValue",
        "description": "Finds all elements whose specified parameter matches a given value (e.g., all walls with 'Mark' == 'W-01').",
        "return_type": "System.Collections.Generic.List<Autodesk.Revit.DB.Element>",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.BuiltInCategory", "Autodesk.Revit.DB.BuiltInParameter", "object", "boolean"]
    },

    # === 2. MANEJO DE TIPOS (DUPLICAR Y MODIFICAR) ===
    {
        "name": "ElementType.DuplicateAndRename",
        "description": "Duplicates an existing ElementType (like FamilySymbol, WallType, etc.) to create a new type with a new name. This is the first step before modifying a type.",
        "return_type": "Autodesk.Revit.DB.ElementType",
        "parameter_types": ["Autodesk.Revit.DB.ElementType", "string"]
    },
    {
        "name": "FamilySymbol.Activate",
        "description": "Activates a FamilySymbol if it is not already active. This is required before it can be used to create an instance.",
        "return_type": "void",
        "parameter_types": ["Autodesk.Revit.DB.FamilySymbol"]
    },
    {
        "name": "FamilySymbol.DuplicateAndSetDimensions",
        "description": "Duplicates a symbol, renames it, and sets its 'Width' and 'Height' parameters. Perfect for creating custom-sized windows or doors.",
        "return_type": "Autodesk.Revit.DB.FamilySymbol",
        "parameter_types": ["Autodesk.Revit.DB.FamilySymbol", "string", "double", "double"]
    },
    {
        "name": "WallType.DuplicateAndSetThickness",
        "description": "Duplicates a WallType, gives it a new name, and sets the width of its core structural layer.",
        "return_type": "Autodesk.Revit.DB.WallType",
        "parameter_types": ["Autodesk.Revit.DB.WallType", "string", "double"]
    },

    # === 3. INTERACCIÓN CON EL USUARIO (UIDOCUMENT) ===
    {
        "name": "UIDocument.PickElement",
        "description": "Prompts the user to select a single element in the Revit UI, returning the selected element.",
        "return_type": "Autodesk.Revit.DB.Element",
        "parameter_types": ["Autodesk.Revit.UI.UIDocument", "string"]
    },
    {
        "name": "UIDocument.GetCurrentSelectionIds",
        "description": "Gets a collection of ElementIds for all elements currently selected by the user.",
        "return_type": "System.Collections.Generic.ICollection<Autodesk.Revit.DB.ElementId>",
        "parameter_types": ["Autodesk.Revit.UI.UIDocument"]
    },

    # === 4. ACCIONES DE MODIFICACIÓN COMUNES ===
    {
        "name": "Element.Move",
        "description": "Moves an element by a given translation vector (XYZ).",
        "return_type": "void",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.ElementId", "Autodesk.Revit.DB.XYZ"]
    },
    {
        "name": "Element.Rotate",
        "description": "Rotates an element around an axis by a given angle in radians.",
        "return_type": "void",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.ElementId", "Autodesk.Revit.DB.Line", "double"]
    },
    {
        "name": "Document.CopyElements",
        "description": "Copies a collection of elements by a given translation vector.",
        "return_type": "System.Collections.Generic.ICollection<Autodesk.Revit.DB.ElementId>",
        "parameter_types": ["Autodesk.Revit.DB.Document", "System.Collections.Generic.ICollection<Autodesk.Revit.DB.ElementId>", "Autodesk.Revit.DB.XYZ"]
    },

    # === 5. GEOMETRÍA Y RELACIONES ===
    {
        "name": "Grid.FindAllIntersections",
        "description": "Finds all intersection points between all grids in a list. Used to place columns at every grid intersection.",
        "return_type": "System.Collections.Generic.List<Autodesk.Revit.DB.XYZ>",
        "parameter_types": ["System.Collections.Generic.List<Autodesk.Revit.DB.Grid>"]
    },
    {
        "name": "Document.JoinElements",
        "description": "Joins the geometry of two elements that intersect.",
        "return_type": "void",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.Element", "Autodesk.Revit.DB.Element"]
    },
    {
        "name": "Wall.PaintFace",
        "description": "Paints a specific face of a wall (e.g., interior or exterior) with a given material.",
        "return_type": "void",
        "parameter_types": ["Autodesk.Revit.DB.Wall", "Autodesk.Revit.DB.ElementId", "Autodesk.Revit.DB.ShellLayerType"]
    },

    # === 6. VISTAS, PLANOS Y ANOTACIONES ===
    {
        "name": "Document.GetActiveView",
        "description": "Gets the currently active view from the document.",
        "return_type": "Autodesk.Revit.DB.View",
        "parameter_types": ["Autodesk.Revit.DB.Document"]
    },
    {
        "name": "Document.CreateSheetAndPlaceView",
        "description": "Creates a new sheet using a title block and places a specified view in its center.",
        "return_type": "Autodesk.Revit.DB.ViewSheet",
        "parameter_types": ["Autodesk.Revit.DB.Document", "Autodesk.Revit.DB.ElementId", "string", "string", "Autodesk.Revit.DB.ElementId"]
    },
    {
        "name": "View.TagAllElementsOfCategory",
        "description": "Places a tag on all elements of a specific category within the given view.",
        "return_type": "void",
        "parameter_types": ["Autodesk.Revit.DB.View", "Autodesk.Revit.DB.BuiltInCategory"]
    },
    {
        "name": "View.SetCategoryVisibility",
        "description": "Hides or shows an entire category of elements within a specific view.",
        "return_type": "void",
        "parameter_types": ["Autodesk.Revit.DB.View", "Autodesk.Revit.DB.BuiltInCategory", "boolean"]
    }
]

def main():
    """
    Lee el catálogo original de la API de Revit, le añade los helpers
    conceptuales definidos arriba y guarda el resultado en un nuevo archivo JSON.
    """
    try:
        with open(CATALOG_IN, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Archivo de catálogo de entrada no encontrado en '{CATALOG_IN}'")
        return

    existing_names = {item['name'] for item in catalog}
    new_helpers = [helper for helper in HELPERS if helper['name'] not in existing_names]
    catalog.extend(new_helpers)
    
    with open(CATALOG_OUT, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Catálogo enriquecido con {len(new_helpers)} nuevos helpers generado en:\n{CATALOG_OUT}")

if __name__ == "__main__":
    main()